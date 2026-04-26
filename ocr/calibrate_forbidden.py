"""
의사랑 PHI strip 8필드 좌표 캘리브레이션 (Session 6 P1, Phase 1 - C3-B)
실행: python ocr/calibrate_forbidden.py

목적:
    1. forbidden_regions.json 생성 (PHI 보호 6필드, _status: active)
    2. regions.json 의 patient_context 영역 자동 계산 + 메타 도입
    3. 사후 검증: assert_regions_safe(strict=True) 통과 확인

PHI strip 8필드 (의사랑 화면 순서):
    [1] 환자번호    forbidden  → patient_no
    [2] 이름        forbidden  → patient_name
    [3] 주민번호    forbidden  → patient_rrn
    [4] 성별        capture    → patient_context 좌상단 정의
    [5] 나이        capture    → patient_context 우하단 정의
    [6] 보험종류    forbidden  → insurance_type
    [7] 보험번호    forbidden  → insurance_id
    [8] 보호자이름  forbidden  → guardian_name
    (제외: 휴대폰번호 — 의사랑 화면 미표시)

총 측정: 8필드 × 2점 = 16 Enter

사용:
    python ocr/calibrate_forbidden.py            # 실제 측정 (진료실)
    python ocr/calibrate_forbidden.py --check    # 의존성/환경 검증만

전제:
    - 의사랑 EMR 화면이 열려있고 PHI strip 이 화면 하단에 보여야 함
    - pyautogui, keyboard 패키지 설치되어 있어야 함

안전:
    - 측정 시작 전 regions.json / forbidden_regions.json 자동 백업 (.bak)
    - 사후 검증 실패 시 자동 복원
    - 중간 Ctrl+C: 백업 그대로, 실제 파일은 변경 안 됨

참조 문서:
    - decision-2026-04-21-capture-regions-and-rules.md §2 (PHI forbidden zone)
    - design/system-overview-v3.md §11.7
"""
import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime


# ─────────────────────────────────────────────────────────────
# 경로
# ─────────────────────────────────────────────────────────────
_DIR = os.path.dirname(os.path.abspath(__file__))
REGIONS_PATH = os.path.join(_DIR, "regions.json")
FORBIDDEN_PATH = os.path.join(_DIR, "forbidden_regions.json")
REGIONS_BAK = REGIONS_PATH + ".bak"
FORBIDDEN_BAK = FORBIDDEN_PATH + ".bak"

# forbidden_zone 모듈 import 경로 보장
sys.path.insert(0, _DIR)


# ─────────────────────────────────────────────────────────────
# PHI strip 필드 정의
# ─────────────────────────────────────────────────────────────
# (key, label, kind, desc)
PHI_STRIP_FIELDS = [
    ("patient_no",     "환자번호",     "forbidden", "환자번호 (의사랑 내부 ID)"),
    ("patient_name",   "이름",         "forbidden", "환자 이름"),
    ("patient_rrn",    "주민번호",     "forbidden", "주민등록번호"),
    ("sex",            "성별",         "capture",   "성별 (patient_context 좌상단)"),
    ("age",            "나이",         "capture",   "나이 (patient_context 우하단)"),
    ("insurance_type", "보험종류",     "forbidden", "보험종류"),
    ("insurance_id",   "보험번호",     "forbidden", "보험번호"),
    ("guardian_name",  "보호자이름",   "forbidden", "보호자 이름"),
]


# ─────────────────────────────────────────────────────────────
# 환경 검증
# ─────────────────────────────────────────────────────────────
def check_environment(verbose: bool = True) -> bool:
    """의존성 / 파일 위치 검증. 실제 측정 없이 환경만 점검."""
    ok = True

    if verbose:
        print("[환경 검증]")

    # 1. forbidden_zone.py 존재
    fz_path = os.path.join(_DIR, "forbidden_zone.py")
    if os.path.exists(fz_path):
        if verbose:
            print(f"  [OK]   forbidden_zone.py: {fz_path}")
    else:
        print(f"  [FAIL] forbidden_zone.py 없음: {fz_path}")
        ok = False

    # 2. forbidden_zone 모듈 import 가능 + assert_regions_safe 함수 존재
    try:
        from forbidden_zone import assert_regions_safe, init_placeholder
        if verbose:
            print(f"  [OK]   forbidden_zone 모듈 import 성공")
    except Exception as e:
        print(f"  [FAIL] forbidden_zone import 실패: {e}")
        ok = False

    # 3. pyautogui / keyboard
    # (Exception 으로 넓게 잡음. ImportError 외에 X display 미연결 등의 환경 오류도 포착)
    try:
        import pyautogui
        if verbose:
            print(f"  [OK]   pyautogui import 성공")
    except ImportError:
        print(f"  [FAIL] pyautogui 없음. pip install pyautogui")
        ok = False
    except Exception as e:
        print(f"  [FAIL] pyautogui import 오류 (환경 문제): {e}")
        ok = False

    try:
        import keyboard
        if verbose:
            print(f"  [OK]   keyboard import 성공")
    except ImportError:
        print(f"  [FAIL] keyboard 없음. pip install keyboard")
        ok = False
    except Exception as e:
        print(f"  [FAIL] keyboard import 오류 (환경 문제): {e}")
        ok = False

    # 4. ocr 디렉토리 쓰기 권한
    if os.access(_DIR, os.W_OK):
        if verbose:
            print(f"  [OK]   ocr 디렉토리 쓰기 가능: {_DIR}")
    else:
        print(f"  [FAIL] ocr 디렉토리 쓰기 불가: {_DIR}")
        ok = False

    return ok


# ─────────────────────────────────────────────────────────────
# 측정 함수
# ─────────────────────────────────────────────────────────────
def wait_enter_and_get_position(prompt: str) -> tuple:
    """Enter 누른 시점의 마우스 좌표 반환."""
    import pyautogui
    import keyboard

    print(f"    → {prompt}")
    print(f"      (마우스 이동 후 Enter)")
    time.sleep(0.3)   # 이전 Enter 잔여 입력 회피
    keyboard.wait("enter")
    x, y = pyautogui.position()
    print(f"      좌표 기록: ({x}, {y})")
    return (x, y)


def measure_field(idx: int, total: int, key: str, label: str, kind: str) -> dict:
    """단일 필드 좌상단/우하단 측정."""
    print()
    if kind == "forbidden":
        print(f"[{idx}/{total}] {label}  (forbidden — PHI 보호 대상, 캡처 안 됨)")
    else:
        print(f"[{idx}/{total}] {label}  (capture — 캡처됨, 좁게 잡으세요)")

    x1, y1 = wait_enter_and_get_position(f"{label} 칸의 [좌상단] 위치")
    x2, y2 = wait_enter_and_get_position(f"{label} 칸의 [우하단] 위치")

    # bbox 유효성 즉시 검증
    if x2 <= x1 or y2 <= y1:
        print(f"  [WARN] bbox 비정상 (x2≤x1 또는 y2≤y1). 좌표 입력 순서 확인.")
        print(f"  → 다시 측정 합니다.")
        return measure_field(idx, total, key, label, kind)

    return {"x1": x1, "y1": y1, "x2": x2, "y2": y2}


def measure_all() -> dict:
    """8필드 모두 측정. dict[key] = bbox 반환."""
    measurements = {}
    total = len(PHI_STRIP_FIELDS)
    for i, (key, label, kind, _desc) in enumerate(PHI_STRIP_FIELDS, start=1):
        measurements[key] = measure_field(i, total, key, label, kind)
    return measurements


# ─────────────────────────────────────────────────────────────
# 데이터 구축
# ─────────────────────────────────────────────────────────────
def build_forbidden_regions(measurements: dict) -> dict:
    """forbidden 6필드만 골라 forbidden_regions.json 구조 작성."""
    forbidden = {
        "_schema_version": 1,
        "_status": "active",
        "_calibrated_at": datetime.now().isoformat(timespec="seconds"),
        "_note": "calibrate_forbidden.py 자동 측정. 의사랑 PHI strip 6필드.",
    }
    for key, label, kind, desc in PHI_STRIP_FIELDS:
        if kind != "forbidden":
            continue
        m = measurements[key]
        forbidden[key] = {
            "x1": m["x1"], "y1": m["y1"], "x2": m["x2"], "y2": m["y2"],
            "_desc": desc,
        }
    return forbidden


def build_patient_context(measurements: dict) -> dict:
    """sex / age 측정값의 합집합 bbox 로 patient_context 작성."""
    sex = measurements["sex"]
    age = measurements["age"]
    return {
        "tier": "tier2",
        "x1": min(sex["x1"], age["x1"]),
        "y1": min(sex["y1"], age["y1"]),
        "x2": max(sex["x2"], age["x2"]),
        "y2": max(sex["y2"], age["y2"]),
        "_auto_derived_from_phi_strip": True,
        "_desc": "성별 + 나이 (parse_patient_context 입력 영역)",
    }


# ─────────────────────────────────────────────────────────────
# regions.json 부분 갱신
# ─────────────────────────────────────────────────────────────
def update_regions_json(patient_context_box: dict) -> str:
    """
    regions.json 부분 갱신.

    동작:
        - 파일 없으면 새로 생성 (메타 + patient_context 만)
        - 평면 구조 (메타 없음, 기존 4영역) 면:
            메타 추가
            기존 4영역에 tier:tier1 추가
            patient_context 추가
        - 이미 메타 구조면 patient_context 만 갱신, _calibrated_at 갱신

    반환: 저장된 파일 경로
    """
    if os.path.exists(REGIONS_PATH):
        with open(REGIONS_PATH, encoding="utf-8") as f:
            regions = json.load(f)
    else:
        regions = {}

    has_meta = "_schema_version" in regions
    now_iso = datetime.now().isoformat(timespec="seconds")

    if not has_meta:
        # 평면 구조 → 메타 도입
        # 기존 영역에 tier:tier1 추가 (placeholder 없음 가정)
        for k in list(regions.keys()):
            v = regions[k]
            if isinstance(v, dict) and "x1" in v and "tier" not in v:
                v["tier"] = "tier1"

        # 메타 + 기존 영역 + patient_context 순서로 새 dict
        new_regions = {
            "_schema_version": 2,
            "_layout_version": "uisarang_2026_04",
            "_calibrated_at": now_iso,
            "_note": "tier1 = 핵심 임상 영역, tier2 = 컨텍스트 영역.",
        }
        new_regions.update(regions)
        regions = new_regions
    else:
        regions["_calibrated_at"] = now_iso

    regions["patient_context"] = patient_context_box

    with open(REGIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(regions, f, indent=2, ensure_ascii=False)

    return REGIONS_PATH


def save_forbidden_regions(forbidden: dict) -> str:
    with open(FORBIDDEN_PATH, "w", encoding="utf-8") as f:
        json.dump(forbidden, f, indent=2, ensure_ascii=False)
    return FORBIDDEN_PATH


# ─────────────────────────────────────────────────────────────
# 백업 / 복원
# ─────────────────────────────────────────────────────────────
def backup_existing():
    """기존 파일 백업. 둘 다 옵션."""
    if os.path.exists(REGIONS_PATH):
        shutil.copy2(REGIONS_PATH, REGIONS_BAK)
    if os.path.exists(FORBIDDEN_PATH):
        shutil.copy2(FORBIDDEN_PATH, FORBIDDEN_BAK)


def restore_from_backup():
    """백업에서 복원. 백업이 없으면 (=원래 없던 파일) 현재 생성된 거 삭제."""
    if os.path.exists(REGIONS_BAK):
        shutil.copy2(REGIONS_BAK, REGIONS_PATH)
    elif os.path.exists(REGIONS_PATH):
        # 원래 없던 파일을 새로 만들었던 경우 삭제
        os.unlink(REGIONS_PATH)

    if os.path.exists(FORBIDDEN_BAK):
        shutil.copy2(FORBIDDEN_BAK, FORBIDDEN_PATH)
    elif os.path.exists(FORBIDDEN_PATH):
        os.unlink(FORBIDDEN_PATH)


def cleanup_backup():
    """검증 통과 후 백업 삭제."""
    for p in (REGIONS_BAK, FORBIDDEN_BAK):
        if os.path.exists(p):
            os.unlink(p)


# ─────────────────────────────────────────────────────────────
# 사후 검증
# ─────────────────────────────────────────────────────────────
def verify_safety() -> tuple:
    """
    저장된 regions.json + forbidden_regions.json 으로 strict 검증.
    반환: (ok: bool, error_msg: str)
    """
    from forbidden_zone import assert_regions_safe

    with open(REGIONS_PATH, encoding="utf-8") as f:
        regions = json.load(f)
    with open(FORBIDDEN_PATH, encoding="utf-8") as f:
        forbidden = json.load(f)

    try:
        assert_regions_safe(regions, forbidden, strict=True)
        return True, ""
    except RuntimeError as e:
        return False, str(e)


# ─────────────────────────────────────────────────────────────
# 결과 요약
# ─────────────────────────────────────────────────────────────
def print_summary(measurements: dict, forbidden: dict, pc_box: dict):
    print()
    print("=" * 60)
    print("  측정 결과 요약")
    print("=" * 60)

    print("\n[forbidden_regions.json] (6필드, _status: active)")
    for key, label, kind, _desc in PHI_STRIP_FIELDS:
        if kind != "forbidden":
            continue
        m = measurements[key]
        print(f"  {label:8s} {key:16s} ({m['x1']:4d},{m['y1']:4d}) → ({m['x2']:4d},{m['y2']:4d})")

    print("\n[regions.json patient_context] (성별 + 나이 합집합)")
    sex = measurements["sex"]
    age = measurements["age"]
    print(f"  성별 측정          ({sex['x1']:4d},{sex['y1']:4d}) → ({sex['x2']:4d},{sex['y2']:4d})")
    print(f"  나이 측정          ({age['x1']:4d},{age['y1']:4d}) → ({age['x2']:4d},{age['y2']:4d})")
    print(f"  patient_context    ({pc_box['x1']:4d},{pc_box['y1']:4d}) → ({pc_box['x2']:4d},{pc_box['y2']:4d})")
    print(f"                     (자동 계산: 두 영역의 합집합)")

    print()
    print("=" * 60)
    print("  다음 단계:")
    print("    Phase 1 종료. 데스크탑/노트북에서 Phase 3 patch 진행.")
    print("    이 PC 의 regions.json / forbidden_regions.json 은 보존됩니다.")
    print("=" * 60)


# ─────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────
def main_check():
    """--check 모드. 의존성/환경만 검증."""
    print("=" * 60)
    print("  calibrate_forbidden.py — 환경 검증 (--check)")
    print("=" * 60)
    print()
    if check_environment(verbose=True):
        print("\n[OK] 모든 검증 통과. 측정 가능 상태입니다.")
        return 0
    else:
        print("\n[FAIL] 일부 검증 실패. 위 항목 해결 후 재시도.")
        return 1


def main_calibrate():
    """실제 측정 모드."""
    print("=" * 70)
    print("  의사랑 PHI strip 8필드 캘리브레이션")
    print("=" * 70)
    print()
    print("  의사랑 EMR 을 열고 환자 차트가 표시된 상태여야 합니다.")
    print("  PHI strip (화면 하단 한 줄) 이 보여야 합니다.")
    print()
    print("  각 필드마다 [좌상단] → [우하단] 으로 마우스를 옮기고 Enter.")
    print("  총 8필드 × 2점 = 16번 Enter 입력 필요.")
    print()
    print("  중간 그만두기: Ctrl+C")
    print("  (저장된 파일은 변경되지 않습니다)")
    print()
    print("=" * 70)

    # 환경 검증
    if not check_environment(verbose=False):
        print("\n[FAIL] 환경 검증 실패. python ocr/calibrate_forbidden.py --check 로 상세 확인.")
        return 1

    # 백업
    backup_existing()

    try:
        # 측정 (16 Enter)
        measurements = measure_all()

        # 데이터 구축
        forbidden = build_forbidden_regions(measurements)
        pc_box = build_patient_context(measurements)

        # 저장
        fp = save_forbidden_regions(forbidden)
        rp = update_regions_json(pc_box)
        print(f"\n[저장] {fp}")
        print(f"[저장] {rp}")

        # 사후 검증
        print("\n[검증] forbidden_zone.assert_regions_safe(strict=True) ...")
        ok, err = verify_safety()
        if not ok:
            print(f"\n[FAIL] 검증 실패:")
            print(f"  {err}")
            print()
            print("  대부분 patient_context (성별 + 나이) 가 다른 forbidden 필드와 겹친 경우입니다.")
            print("  - 성별 / 나이 영역을 더 좁게 잡아 재측정 필요")
            print("  - 좌우의 주민번호 / 보험종류 칸과 겹치지 않도록 주의")
            print()
            print("  → 백업에서 복원 중...")
            restore_from_backup()
            print("  → 복원 완료. python ocr/calibrate_forbidden.py 로 재측정.")
            return 1

        print("[OK] strict=True 검증 통과.")

        # 백업 정리
        cleanup_backup()

        # 결과 요약
        print_summary(measurements, forbidden, pc_box)
        return 0

    except KeyboardInterrupt:
        print("\n\n[중단] Ctrl+C 입력. 백업에서 복원 중...")
        restore_from_backup()
        print("[OK] 복원 완료. 저장된 파일 변경 없음.")
        return 130

    except Exception as e:
        print(f"\n[ERROR] 예상치 못한 오류: {e}")
        print("  백업에서 복원 중...")
        restore_from_backup()
        print("  복원 완료.")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="의사랑 PHI strip 8필드 캘리브레이션",
    )
    parser.add_argument("--check", action="store_true",
                        help="의존성/환경 검증만 수행 (실제 측정 없음)")
    args = parser.parse_args()

    if args.check:
        sys.exit(main_check())
    else:
        sys.exit(main_calibrate())


if __name__ == "__main__":
    main()
