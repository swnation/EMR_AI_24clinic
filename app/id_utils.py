r"""
Session ID / Patient Key / Local Salt 관리 유틸

참조 문서:
    - decision-2026-04-21-patient-identifier-policy.md §2
    - design/system-overview-v3.md §11.5 (2-Tier 저장 구조)

제공 함수:
    - make_session_id()          → 진료실 PC ↔ 집 PC 공용 교환 키
    - make_patient_key(patient_no) → 운영 DB 내부 환자 추적 키 (외부 유출 금지)
    - get_or_create_local_salt() → patient_key 해시용 로컬 시크릿

설계 결정 (결정 문서 §2 미확정 항목을 본 파일에서 확정):
    1. Hash 알고리즘: HMAC-SHA256 의 앞 16 hex (= 64bit).
       - Patch A (2026-04-24): 8 hex(32bit) → 16 hex(64bit) 로 확장.
         근거: 생일 문제. 32bit 에서 10,000명 충돌 ≈ 1.16%, 30,000명 ≈ 10%.
         내부 longitudinal join key 로 쓰이므로 1% 도 허용 불가. 64bit 면
         100,000명에서도 충돌 ≈ 2.7e-10, 실질 0.
       - HMAC 구조 사용: concat (patient_no + salt) 은 ambiguity 존재.
         salt 를 secret key 로 쓰는 구조는 HMAC 이 정석.
    2. local_salt 저장 경로: %LOCALAPPDATA%\ClinicalAssist\local_salt
       - Windows 기본 NTFS ACL 이 같은 PC 의 다른 사용자 계정 접근을 차단함
         (단, 간호 인력과 같은 Windows 계정을 공유하면 이 방어선은 무력 → 운영 정책 이슈)
       - 네트워크 로밍 대상 아님 (APPDATA 가 아니라 LOCALAPPDATA)
    3. 엔트로피: 16 bytes = 32 hex chars = 128bit (결정 문서 규정 그대로).
    4. 손상 감지: 파일이 존재하는데 32 hex 가 아니면 자동 재생성하지 않고 raise.
       자동 재생성 시 기존 patient_key 전부 무효화되므로 명시적 수동 복구를 강제.
    5. 교체 주기: 코드가 자동 교체하지 않음. 결정 문서 §2.2 에 따라
       (1) PC 초기화/교체 (2) 유출 의심 시에만 파일 수동 삭제 후 재실행.
    6. patient_no 는 **문자열 전용**. int 입력 거부.
       - Patch A: EMR 환자번호가 "0012345" (leading zero) / "C-00123" (prefix)
         형태일 수 있으므로 int 변환 시 정보 손실. 명시적 TypeError.
"""
import hashlib
import hmac
import os
import secrets
import sys
import uuid
from datetime import datetime
from pathlib import Path


# ─────────────────────────────────────────────────────────────
# 설정 상수
# ─────────────────────────────────────────────────────────────
SALT_DIR_NAME = "ClinicalAssist"
SALT_FILE_NAME = "local_salt"
SALT_LENGTH_HEX = 32            # 16 bytes = 32 hex chars
PATIENT_KEY_LENGTH = 16         # HMAC-SHA256 앞 16 hex (= 64bit). Patch A: 8 → 16.


# ─────────────────────────────────────────────────────────────
# 내부: 저장 경로
# ─────────────────────────────────────────────────────────────
def _get_salt_path() -> Path:
    r"""
    local_salt 파일 경로.

    Windows 진료실 PC: %LOCALAPPDATA%\ClinicalAssist\local_salt
    개발용(Linux/Mac): ~/.local/share/ClinicalAssist/local_salt
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        if not base:
            raise RuntimeError(
                "LOCALAPPDATA 환경변수가 없다. Windows 진료실 PC 환경인지 확인."
            )
        return Path(base) / SALT_DIR_NAME / SALT_FILE_NAME
    # 개발용 fallback
    return Path.home() / ".local" / "share" / SALT_DIR_NAME / SALT_FILE_NAME


def _is_valid_hex_salt(s) -> bool:
    # Patch A+ minor: 문자열이 아닌 값(None, int 등)도 False 로 안전하게 반환.
    # 이전엔 len() 에서 TypeError 가 날 수 있었음.
    if not isinstance(s, str):
        return False
    if len(s) != SALT_LENGTH_HEX:
        return False
    try:
        int(s, 16)
        return True
    except ValueError:
        return False


# ─────────────────────────────────────────────────────────────
# 공개 API
# ─────────────────────────────────────────────────────────────
def get_or_create_local_salt() -> str:
    """
    local_salt 를 읽어오거나, 없으면 새로 생성해서 반환.

    Returns:
        32자리 hex 문자열

    Raises:
        RuntimeError: 파일이 존재하는데 손상(32 hex 아님)된 경우
                      — 자동 복구하지 않음. 백업에서 복구하거나 의도적으로 삭제 후 재실행 필요.
    """
    salt_path = _get_salt_path()

    if salt_path.exists():
        salt = salt_path.read_text(encoding="utf-8").strip()
        if not _is_valid_hex_salt(salt):
            raise RuntimeError(
                f"local_salt 파일 손상: {salt_path}\n"
                f"32자리 hex 형식이 아님. 자동 복구하지 않는다.\n"
                f"  - 백업본이 있으면 해당 위치에 복원할 것.\n"
                f"  - 백업이 없고 재생성하려면 파일을 지우고 이 함수를 다시 호출."
                f"   (단, 기존 운영 DB 의 patient_key 들은 전부 무효화됨)"
            )
        return salt

    # 최초 생성
    salt_path.parent.mkdir(parents=True, exist_ok=True)
    salt = secrets.token_hex(SALT_LENGTH_HEX // 2)
    # 원자적 쓰기(같은 드라이브의 임시 파일 → rename)
    tmp_path = salt_path.with_suffix(salt_path.suffix + ".tmp")
    tmp_path.write_text(salt, encoding="utf-8")
    os.replace(tmp_path, salt_path)

    print(f"[id_utils] local_salt 최초 생성: {salt_path}")
    print(f"[id_utils] ! 중요: 이 파일을 분실하면 기존 patient_key 재현 불가.")
    print(f"[id_utils] ! 내부망 서버에 암호화 백업 정책 적용 필요.")

    return salt


def make_session_id() -> str:
    """
    session_id 생성 (진료실 PC ↔ 집 PC 공용 교환 키).

    형식: {YYYYMMDD}-{HHMMSS}-{uuid8}
    예:   20260421-234412-a3f8b2e1

    환자 식별 정보 없음. 시각 정보만 포함.
    """
    now = datetime.now()
    return f"{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}-{uuid.uuid4().hex[:8]}"


def make_patient_key(patient_no, salt: str = None) -> str:
    """
    patient_key 생성 (운영 DB 내부 전용, 집 PC 전송 절대 금지).

    Args:
        patient_no: 의사랑 환자번호. **문자열 전용.**
            int 를 넘기면 TypeError — "0012345" (leading zero) 나
            "C-00123" (prefix) 형태가 있을 경우 int 변환으로 정보가 사라지기 때문.
        salt: local_salt (32 hex 문자열). None 이면 자동 로드.

    Returns:
        16자리 hex 문자열 (64bit). 예: "5c3a8f1e9d2b7c6a"

    Raises:
        TypeError:  patient_no 가 문자열이 아닌 경우.
        ValueError: patient_no 가 빈 문자열/공백이거나, salt 가 32 hex 형식이 아닌 경우.

    같은 patient_no + 같은 salt → 항상 같은 patient_key.
    HMAC-SHA256 구조 사용 (Patch A): salt 를 secret key 로 취급.
    concat 방식의 ambiguity (예: "a"+"bc" vs "ab"+"c") 회피.
    """
    # 1. patient_no 타입/값 검증
    if not isinstance(patient_no, str):
        raise TypeError(
            f"patient_no 는 문자열 전용. 받은 타입: {type(patient_no).__name__}. "
            f"EMR 환자번호가 '0012345' / 'C-00123' 등 leading zero·prefix 를 가질 수 "
            f"있으므로 int 로 변환하면 안 된다."
        )
    patient_no_str = patient_no.strip()
    if not patient_no_str:
        raise ValueError("patient_no is empty or whitespace")

    # 2. salt 로드 및 검증
    if salt is None:
        salt = get_or_create_local_salt()
    if not _is_valid_hex_salt(salt):
        # Patch A+ minor: salt 가 비문자열이어도 len() 에서 TypeError 나지 않게 안전하게 메시지 구성.
        salt_info = f"len={len(salt)}" if isinstance(salt, str) else f"type={type(salt).__name__}"
        raise ValueError(
            f"salt 는 {SALT_LENGTH_HEX} hex 문자열이어야 함. 받은 값: {salt_info}"
        )

    # 3. HMAC-SHA256(key=salt_bytes, msg=patient_no_bytes) 의 앞 16 hex
    digest = hmac.new(
        key=bytes.fromhex(salt),
        msg=patient_no_str.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return digest[:PATIENT_KEY_LENGTH]


# ─────────────────────────────────────────────────────────────
# 셀프 테스트 (python id_utils.py 로 실행)
# ─────────────────────────────────────────────────────────────
def _selftest():
    print("=" * 60)
    print("  id_utils 셀프 테스트")
    print("=" * 60)

    salt_path = _get_salt_path()
    salt = get_or_create_local_salt()
    print(f"\n[1] local_salt")
    print(f"    경로: {salt_path}")
    print(f"    값(앞 4자만): {salt[:4]}... (총 {len(salt)}자)")
    assert _is_valid_hex_salt(salt)
    print(f"    ✓ 32자리 hex 형식 OK")

    sid1 = make_session_id()
    sid2 = make_session_id()
    print(f"\n[2] session_id")
    print(f"    샘플 1: {sid1}")
    print(f"    샘플 2: {sid2}")
    assert sid1 != sid2, "session_id 중복"
    assert len(sid1.split("-")) == 3
    print(f"    ✓ 유일성 OK")

    pk1 = make_patient_key("12345")
    pk2 = make_patient_key("12345")
    pk3 = make_patient_key("67890")
    pk_leading_zero = make_patient_key("0012345")   # 앞에 0
    pk_with_prefix  = make_patient_key("C-00123")   # prefix 포함
    print(f"\n[3] patient_key (HMAC-SHA256, 16 hex)")
    print(f"    make_patient_key('12345'):     {pk1}")
    print(f"    make_patient_key('12345') 재실행: {pk2}")
    print(f"    make_patient_key('67890'):     {pk3}")
    print(f"    make_patient_key('0012345'):   {pk_leading_zero}")
    print(f"    make_patient_key('C-00123'):   {pk_with_prefix}")
    assert pk1 == pk2, "같은 입력인데 결과가 다름"
    assert pk1 != pk3, "다른 입력인데 결과가 같음"
    assert pk1 != pk_leading_zero, "leading zero 가 int 변환되어 사라짐"
    assert pk1 != pk_with_prefix, "prefix 가 무시됨"
    assert len(pk1) == PATIENT_KEY_LENGTH == 16
    print(f"    ✓ 재현성 OK")
    print(f"    ✓ 환자 구분 OK")
    print(f"    ✓ leading zero / prefix 보존 OK")
    print(f"    ✓ 길이 16 hex 확인")

    # 에러 케이스
    print(f"\n[4] 에러 케이스")
    # int 거부
    try:
        make_patient_key(12345)
    except TypeError as e:
        print(f"    ✓ patient_no=12345 (int) → TypeError (Patch A)")
    else:
        raise AssertionError("int 거부 안 됨")
    # None / 빈 문자열
    for bad in [""]:
        try:
            make_patient_key(bad)
        except ValueError:
            print(f"    ✓ patient_no={bad!r} → ValueError (예상대로)")
        else:
            raise AssertionError(f"patient_no={bad!r} 에서 예외 안 나옴")
    # 공백
    try:
        make_patient_key("   ")
    except ValueError:
        print(f"    ✓ patient_no='   ' → ValueError (예상대로)")
    # 잘못된 salt
    try:
        make_patient_key("12345", salt="not-32-hex")
    except ValueError as e:
        print(f"    ✓ 잘못된 salt (짧은 문자열) → ValueError (Patch A)")
    else:
        raise AssertionError("잘못된 salt 허용됨")
    # Patch A+ minor: salt 가 비문자열 (int, bytes 등) 일 때도 ValueError 로 안전 처리.
    # None 은 "자동 로드" 신호이므로 여기에 포함하지 않음.
    for bad_salt in [12345, b"\x00" * 32]:
        try:
            make_patient_key("12345", salt=bad_salt)
        except ValueError:
            pass  # 예상대로
        except TypeError:
            raise AssertionError(f"salt={bad_salt!r} 에서 TypeError — Patch A+ 에서 ValueError 로 정리돼야 함")
        else:
            raise AssertionError(f"salt={bad_salt!r} 이 통과함")
    print(f"    ✓ 비문자열 salt (int/bytes) → ValueError (Patch A+)")

    print("\n모든 테스트 통과.")


if __name__ == "__main__":
    _selftest()
