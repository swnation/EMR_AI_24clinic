"""
Age 분류/판정 유틸 (v3 §11.8 / Decision D1 §4 의 16구간 체계)

참조 문서:
    - decisions/decision-2026-04-21-patient-identifier-policy.md §4
    - design/system-overview-v3.md §11.8

제공:
    - AGE_MINOR_LABELS                : 16구간 전체 집합 (오타 검증용)
    - AGE_MINOR_UNDER_12              : 12세 미만 = 소아 BW rule 대상 6구간
    - is_age_minor_under_12(...)      : age_minor 또는 age_years 로 소아 판정 (unknown 가능)

원칙:
    1. 본 모듈은 **parser.py 의 역할을 대체하지 않는다**. 이미 계산된 age_minor /
       age_years 를 받아 rule 발동 여부 판정용 헬퍼만 제공.
    2. age_minor 가 공식 경로 (parser 출력). age_years 는 폴백.
    3. "6개월 미만" 및 "정보 없음" 케이스는 항상 None 반환 = unknown.
       소아 BW rule 측에서 severity=unknown 처리하게 둔다.
    4. parser.py 가 향후 16구간 출력으로 확장되면 여기 상수를 그대로 import 해서 쓴다.
"""
from typing import Optional


# ─────────────────────────────────────────────────────────────
# Age 분류 상수 (v3 §11.8.1 Level 2, 16구간)
# ─────────────────────────────────────────────────────────────

AGE_MINOR_LABELS = frozenset({
    # 10세 미만 (5구간; 6개월 미만은 집계 대상 외)
    "6개월~1세", "1~2세", "2~6세", "6~9세", "9~10세",
    # 10대 (4구간)
    "10~12세", "12~15세", "15~18세", "18~19세",
    # 20대~70대 (6구간)
    "20대", "30대", "40대", "50대", "60대", "70대",
    # 80세 이상 (1구간)
    "80세_이상",
})

# 소아 BW rule 발동 대상: 12세 미만 = 위 6구간.
# Decision D3 §5 / v3 §8.5.1 원문의 목록 그대로.
AGE_MINOR_UNDER_12 = frozenset({
    "6개월~1세", "1~2세", "2~6세", "6~9세", "9~10세", "10~12세",
})

# sanity: UNDER_12 는 전체의 부분집합이어야 함.
assert AGE_MINOR_UNDER_12 <= AGE_MINOR_LABELS, \
    "AGE_MINOR_UNDER_12 에 AGE_MINOR_LABELS 밖 값 포함됨. 오타 점검 필요."


# ─────────────────────────────────────────────────────────────
# 소아 (12세 미만) 판정
# ─────────────────────────────────────────────────────────────
def is_age_minor_under_12(
    age_minor: Optional[str] = None,
    age_years: Optional[int] = None,
) -> Optional[bool]:
    """
    해당 환자가 12세 미만인지 판정.

    반환:
        True   : 12세 미만 (소아 BW rule 발동 대상 구간).
        False  : 12세 이상 또는 6개월 미만 (rule 대상 외).
        None   : 정보 부족 → 호출측에서 severity=unknown 처리해야 함.

    우선순위:
        1. age_minor 가 주어지고 AGE_MINOR_LABELS 에 포함 → 그 값으로 판정.
           - AGE_MINOR_UNDER_12 에 있으면 True, 아니면 False.
        2. age_minor 없고 age_years 만 있음:
           - 1 <= age_years < 12 → True   (6개월~1세는 int 변환 시 0 이므로 age_years 만으로는 배제)
           - age_years >= 12 → False
           - age_years < 1 → None (부족. parser 가 age_minor 채워야 함)
           - age_years < 0 → ValueError (명백한 오류)
        3. 둘 다 없음 → None.

    6개월~1세 케이스:
        age_years 가 0 또는 None 으로 들어올 수 있음. 이 경우 age_minor 없이
        단정하면 6개월 미만까지 포괄해버려 rule 오발동 위험 → None (unknown).
        parser.py 가 "N개월" 표기 → age_minor="6개월~1세" 로 정확히 채워줘야 정상 동작.

    parser 경로:
        parse_age() → {"age_minor": "...", "age_years": N, ...}
        위 dict 을 unpack 해서 이 함수에 넘기면 됨.
    """
    # ── age_minor 우선 ──
    if age_minor is not None:
        if not isinstance(age_minor, str):
            raise TypeError(
                f"age_minor 는 str 또는 None 이어야 함. got: {type(age_minor).__name__}"
            )
        # 빈 문자열은 "정보 없음" 으로 간주 (parser 가 unknown 반환한 경우).
        if age_minor == "":
            pass  # age_years 폴백으로.
        elif age_minor not in AGE_MINOR_LABELS:
            # 오타 방지. parser 가 정의 외 값을 내보내면 즉시 드러나야 함.
            raise ValueError(
                f"age_minor {age_minor!r} 가 AGE_MINOR_LABELS 에 없음. "
                f"parser 쪽 오타 또는 매핑 누락 점검. 허용: {sorted(AGE_MINOR_LABELS)}"
            )
        else:
            return age_minor in AGE_MINOR_UNDER_12

    # ── age_years 폴백 ──
    if age_years is not None:
        if not isinstance(age_years, (int, float)) or isinstance(age_years, bool):
            # bool 은 int 의 하위타입. True/False 가 1/0 으로 잘못 들어오는 것 차단.
            raise TypeError(
                f"age_years 는 int 또는 None 이어야 함. got: {type(age_years).__name__}"
            )
        if age_years < 0:
            raise ValueError(f"age_years 는 음수일 수 없음. got: {age_years}")
        if age_years < 1:
            # 6개월 미만 / 6개월~1세 경계 모호. parser 가 age_minor 명시해야 정확.
            return None
        if age_years < 12:
            return True
        return False

    # ── 둘 다 없음 ──
    return None


# ─────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # ── age_minor 경로 ──
    assert is_age_minor_under_12(age_minor="2~6세") is True
    assert is_age_minor_under_12(age_minor="10~12세") is True
    assert is_age_minor_under_12(age_minor="6개월~1세") is True
    assert is_age_minor_under_12(age_minor="12~15세") is False
    assert is_age_minor_under_12(age_minor="30대") is False
    assert is_age_minor_under_12(age_minor="80세_이상") is False
    print("[OK] age_minor 6구간 소아 판정")
    print("[OK] age_minor 비소아 판정")

    # ── age_years 폴백 ──
    assert is_age_minor_under_12(age_years=3) is True
    assert is_age_minor_under_12(age_years=11) is True
    assert is_age_minor_under_12(age_years=12) is False
    assert is_age_minor_under_12(age_years=30) is False
    assert is_age_minor_under_12(age_years=80) is False
    print("[OK] age_years 폴백 소아/비소아")

    # ── unknown 반환 케이스 ──
    assert is_age_minor_under_12() is None
    assert is_age_minor_under_12(age_years=0) is None        # 6개월 미만/6개월~1세 경계 모호
    assert is_age_minor_under_12(age_minor="", age_years=0) is None
    print("[OK] 정보 부족 시 unknown 반환")

    # ── age_minor 우선순위 확인 ──
    # age_minor 가 있으면 age_years 는 무시.
    assert is_age_minor_under_12(age_minor="30대", age_years=3) is False
    assert is_age_minor_under_12(age_minor="6개월~1세", age_years=50) is True
    print("[OK] age_minor 우선순위")

    # ── 실패 케이스 ──
    try:
        is_age_minor_under_12(age_minor="10세미만")     # 오타
        raise AssertionError("잘못된 age_minor 가 통과함")
    except ValueError:
        print("[OK] 오타 age_minor 거부")

    try:
        is_age_minor_under_12(age_minor=30)
        raise AssertionError("int age_minor 가 통과함")
    except TypeError:
        print("[OK] int age_minor 거부")

    try:
        is_age_minor_under_12(age_years="30")
        raise AssertionError("str age_years 가 통과함")
    except TypeError:
        print("[OK] str age_years 거부")

    try:
        is_age_minor_under_12(age_years=True)
        raise AssertionError("bool age_years 가 통과함")
    except TypeError:
        print("[OK] bool age_years 거부 (True/False → 1/0 혼동 방지)")

    try:
        is_age_minor_under_12(age_years=-1)
        raise AssertionError("음수 age_years 가 통과함")
    except ValueError:
        print("[OK] 음수 age_years 거부")

    # ── 상수 sanity ──
    assert len(AGE_MINOR_LABELS) == 16
    assert len(AGE_MINOR_UNDER_12) == 6
    print(f"[OK] AGE_MINOR_LABELS 16구간 / UNDER_12 6구간")

    print("\n모든 self-test 통과.")
