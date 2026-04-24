"""
Vitals / OCR 관대 파싱 유틸.

참조:
    - design/system-overview-v3.md §7.5 (unknown 상태 원칙)
    - GPT session 4 patch 의 _coerce_float / _vital_state 아이디어 채택 (2026-04-24)
    - Patch B 적용 (간소화): dict 재귀 탐색 삭제, NaN 체크 추가

제공:
    - coerce_float(value)                       → OCR 노이즈가 낀 문자열에서 숫자 추출
    - is_unknown_value(value)                   → 다양한 "불확실" 표현을 단일하게 판정
    - vital_state(vitals_context, *keys)        → 4상 상태 (unavailable/unknown/present/missing)
    - VITAL_STATE_*                             → 상태 상수

설계 원칙:
    1. OCR 결과는 더럽다. "18kg", "BST 123 mg/dL", " 123 " 같은 입력에서
       숫자만 깔끔하게 뽑는다.
    2. dict 재귀 탐색은 금지. parser 계약 확정 전에 키 이름("value","raw"...)을
       추측하는 건 기술 부채. parser 가 명시적으로 숫자를 넘기거나
       UNCERTAIN_SENTINEL 을 넘기는 방식으로 표준화.
    3. NaN 방어: 스포츠/기기 데이터에 종종 NaN 이 섞임. present 아닌 unknown 으로.
    4. bool 은 int 의 하위타입이라 True/False → 1/0 처럼 오해받을 수 있음. 명시 거부.
    5. vitals_context 자체가 None (legacy pipeline) 이면 unavailable.
       이건 rule 측에서 "현재 파이프라인이 vitals 를 아직 안 주는 중" 으로 해석하여
       legacy backward compat 용 skip 에 사용.
"""
from typing import Any, Optional, Tuple, Union
import re


# ─────────────────────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────────────────────
UNCERTAIN_SENTINEL = "uncertain"

# parser / OCR 이 내뱉을 수 있는 "불확실" 표현들.
# 느슨한 수용은 parser 계약 미확정 기간의 완충. parser 안정 후 UNCERTAIN_SENTINEL 하나로 수렴시킨다.
_UNKNOWN_STR_VALUES = frozenset({
    "", "?", "??", "-", "n/a", "na",
    "unknown", "uncertain", "ocr_failed", "parse_failed", "ambiguous",
})

# vital 상태 enum
VITAL_STATE_UNAVAILABLE = "unavailable"   # vitals_context 자체가 None — pipeline 미연결
VITAL_STATE_UNKNOWN = "unknown"           # 해당 필드 OCR/파싱 불명확
VITAL_STATE_PRESENT = "present"           # 숫자 값 추출 성공
VITAL_STATE_MISSING = "missing"           # 필드는 있으나 값 없음/빈 문자열

_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


# ─────────────────────────────────────────────────────────────
# 숫자 추출
# ─────────────────────────────────────────────────────────────
def coerce_float(value: Any) -> Optional[float]:
    """
    value 에서 float 추출. OCR 노이즈 허용.

    반환:
        float  — 추출 성공.
        None   — 값이 없거나 추출 실패 (NaN, inf 포함).

    허용 입력:
        None, int, float, str (숫자/단위 혼합).

    거부 입력:
        bool (True/False 가 1/0 으로 오해되는 것 차단 → TypeError).
        dict / list / tuple → None 반환 (호출측이 field 접근으로 먼저 풀어야 함).

    예시:
        coerce_float("18kg")         → 18.0
        coerce_float("BST 123")      → 123.0
        coerce_float(" 37.4 ")       → 37.4
        coerce_float("5,0")          → 5.0       # European decimal comma
        coerce_float("12,5kg")       → 12.5      # decimal comma + 단위
        coerce_float("1,234")        → 1234.0    # 천단위 구분 쉼표
        coerce_float("1,234.5")      → 1234.5    # 천단위 + 소수점
        coerce_float("37.4/80")      → 37.4      # 혈압 등 복합값은 첫 숫자만 반환
                                                   # (호출측에서 sbp/dbp 따로 파싱해야 함)
        coerce_float(None)           → None
        coerce_float("")             → None
        coerce_float("uncertain")    → None
        coerce_float(float("nan"))   → None
        coerce_float(True)           → TypeError
    """
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError(
            f"coerce_float 에 bool 값이 들어옴: {value!r}. "
            "True/False 가 1/0 으로 오해될 수 있어 명시 거부. 명확한 숫자/문자열로 전달."
        )
    if isinstance(value, (int, float)):
        f = float(value)
        # NaN / inf 는 숫자이지만 비교 연산이 의도와 다르게 동작 → None 으로.
        if f != f or f in (float("inf"), float("-inf")):
            return None
        return f
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        if s.lower() in _UNKNOWN_STR_VALUES:
            return None
        # 쉼표 처리 분기:
        #   "5,0" / "12,5" 처럼 소수점 자리가 comma 인 European decimal 스타일 → 점으로 변환.
        #   "1,234" / "12,345" 같은 천단위 구분 쉼표 → 제거.
        # 정확한 구별은 불가능하므로 패턴으로 근사:
        #   `^-?\d+,\d{1,2}$` → decimal comma (5,0 / 12,5 / 37,4)
        #   그 외는 thousand separator 로 보고 제거.
        #
        # 주의: "12,5kg" 같이 단위 달린 경우는 먼저 숫자만 분리하지 않으면 패턴 실패.
        # 이 경우엔 첫 숫자 토큰만 뽑아 decimal comma 여부 재판정.
        if "," in s and "." not in s:
            # 숫자+comma+숫자 첫 토큰을 추출해 decimal 판정.
            dec_m = re.match(r"^\s*(-?\d+,\d{1,2})(?:\D|$)", s)
            if dec_m:
                s = dec_m.group(1).replace(",", ".")
            else:
                # 천단위 구분 쉼표로 간주하고 제거.
                s = s.replace(",", "")
        else:
            # "." 가 이미 있으면 쉼표는 천단위 구분으로만 해석 가능.
            s = s.replace(",", "")
        m = _NUMBER_RE.search(s)
        if not m:
            return None
        try:
            f = float(m.group(0))
        except ValueError:
            return None
        if f != f or f in (float("inf"), float("-inf")):
            return None
        return f
    # dict/list/tuple 등은 None. 호출측이 구조 풀어서 재호출해야 함.
    return None


# ─────────────────────────────────────────────────────────────
# 불확실 값 판정
# ─────────────────────────────────────────────────────────────
def is_unknown_value(value: Any) -> bool:
    """
    value 가 "OCR/파싱 불확실" 상태인지.

    True 반환 조건:
        - str 이고 소문자화 후 _UNKNOWN_STR_VALUES 에 있음.
        - dict 이고 "status" 또는 "_status" 가 _UNKNOWN_STR_VALUES 에 있음.
        - dict 이고 "uncertain": True 또는 "parse_failed": True.
        - float 이고 NaN.

    False 반환 조건:
        - None → False. None 은 "값 없음(정상)" 으로 해석. MISSING 과 UNKNOWN 은 별개 개념.
        - 정상 숫자 / 정상 문자열.

    None 을 unknown 으로 취급하지 않는 이유:
        parser 가 "측정 안 함" 과 "파싱 실패" 를 구분해야 하기 때문.
        측정 안 함 = None = missing / 파싱 실패 = UNCERTAIN_SENTINEL = unknown.
    """
    if value is None:
        return False
    if isinstance(value, bool):
        return False
    if isinstance(value, float):
        return value != value   # NaN
    if isinstance(value, str):
        return value.strip().lower() in _UNKNOWN_STR_VALUES
    if isinstance(value, dict):
        status = value.get("status") or value.get("_status")
        if isinstance(status, str) and status.strip().lower() in _UNKNOWN_STR_VALUES:
            return True
        if value.get("uncertain") is True or value.get("parse_failed") is True:
            return True
        return False
    return False


# ─────────────────────────────────────────────────────────────
# vitals_context 필드 접근
# ─────────────────────────────────────────────────────────────
def _ctx_get(context: Any, *keys: str) -> Any:
    """
    dict 에서 key 들 중 하나로 값 조회. 대소문자 무시.
    원본 키 우선 매칭, 없으면 lower 로 재탐색.
    """
    if not isinstance(context, dict):
        return None
    for key in keys:
        if key in context:
            return context[key]
    # 대소문자 무시 폴백
    lowered = {str(k).lower(): v for k, v in context.items()}
    for key in keys:
        lk = str(key).lower()
        if lk in lowered:
            return lowered[lk]
    return None


def vital_state(
    vitals_context: Optional[dict],
    *keys: str,
) -> Tuple[str, Optional[float]]:
    """
    vitals_context 의 특정 필드 상태를 분류.

    반환:
        (state, numeric_value)
        state ∈ {UNAVAILABLE, UNKNOWN, PRESENT, MISSING}
        numeric_value: state=PRESENT 일 때만 float, 그 외는 None.

    state 의미:
        UNAVAILABLE : vitals_context 자체가 None.
                      "파이프라인이 아직 vitals 를 보내지 않음" 시나리오.
                      legacy F12 경로 호환용. rule 측에서 skip 처리.
        UNKNOWN     : 필드가 있지만 OCR/파싱 불확실 ("?", UNCERTAIN_SENTINEL 등).
                      rule 은 severity=unknown 결과를 반환해야 함.
        PRESENT     : 정상 숫자 값 추출 성공.
        MISSING     : 필드 없음 또는 빈 값 (None, "", 빈 dict 등).
                      "측정/기록 안 함" 상태.

    사용 예:
        state, bw = vital_state(vitals, "BW", "bw", "body_weight")
        if state == VITAL_STATE_UNAVAILABLE: return  # 파이프라인 미연결, skip
        if state == VITAL_STATE_UNKNOWN:     return [unknown_result]
        if state == VITAL_STATE_MISSING:     bw 없음으로 rule 분기 (예: unknown)
        # state == PRESENT
        if bw < 10: ...
    """
    if vitals_context is None:
        return VITAL_STATE_UNAVAILABLE, None
    if not isinstance(vitals_context, dict):
        raise TypeError(
            f"vitals_context 는 dict 또는 None 이어야 함. got: {type(vitals_context).__name__}"
        )

    raw = _ctx_get(vitals_context, *keys)

    # 빈 값 처리가 먼저. None / "" 는 MISSING.
    if raw is None:
        return VITAL_STATE_MISSING, None
    if isinstance(raw, str) and raw.strip() == "":
        return VITAL_STATE_MISSING, None

    # 불확실 표현 검사
    if is_unknown_value(raw):
        return VITAL_STATE_UNKNOWN, None

    # 숫자 추출 시도
    numeric = coerce_float(raw)
    if numeric is not None:
        return VITAL_STATE_PRESENT, numeric

    # 숫자 추출 실패 + 불확실도 아님 → 안전쪽으로 UNKNOWN.
    # (예: "고혈당 의심" 같은 임상 메모가 BST 필드에 들어온 케이스)
    return VITAL_STATE_UNKNOWN, None


# ─────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # ── coerce_float ──
    assert coerce_float(18) == 18.0
    assert coerce_float(37.4) == 37.4
    assert coerce_float("18") == 18.0
    assert coerce_float("18kg") == 18.0
    assert coerce_float("BST 123") == 123.0
    assert coerce_float(" 37.4 ") == 37.4
    assert coerce_float("123 mg/dL") == 123.0
    assert coerce_float("-5") == -5.0
    # Comma 처리 (2026-04-24 GPT redline #1)
    assert coerce_float("5,0") == 5.0          # European decimal comma
    assert coerce_float("12,5") == 12.5
    assert coerce_float("12,5kg") == 12.5
    assert coerce_float("37,4") == 37.4
    assert coerce_float("1,234") == 1234.0     # thousand separator
    assert coerce_float("12,345") == 12345.0
    assert coerce_float("1,234.5") == 1234.5   # thousand + decimal
    assert coerce_float(None) is None
    assert coerce_float("") is None
    assert coerce_float("   ") is None
    assert coerce_float("uncertain") is None
    assert coerce_float("?") is None
    assert coerce_float(float("nan")) is None
    assert coerce_float(float("inf")) is None
    assert coerce_float({"value": 10}) is None       # dict 재귀 탐색 안 함
    assert coerce_float([1, 2]) is None
    print("[OK] coerce_float 다양 입력")

    try:
        coerce_float(True)
        raise AssertionError("bool 이 통과")
    except TypeError:
        print("[OK] coerce_float bool 거부")

    # ── is_unknown_value ──
    assert is_unknown_value(None) is False         # None 은 MISSING 이지 UNKNOWN 아님
    assert is_unknown_value(123) is False
    assert is_unknown_value(37.4) is False
    assert is_unknown_value("123") is False
    assert is_unknown_value("?") is True
    assert is_unknown_value("??") is True
    assert is_unknown_value("uncertain") is True
    assert is_unknown_value("UNCERTAIN") is True   # 대소문자 무시
    assert is_unknown_value("ocr_failed") is True
    assert is_unknown_value("") is True            # 빈 문자열도 여기서는 unknown
    assert is_unknown_value(float("nan")) is True
    assert is_unknown_value({"status": "unknown"}) is True
    assert is_unknown_value({"_status": "ambiguous"}) is True
    assert is_unknown_value({"uncertain": True}) is True
    assert is_unknown_value({"parse_failed": True}) is True
    assert is_unknown_value({"value": 10}) is False
    print("[OK] is_unknown_value 분기")

    # ── vital_state ──
    # unavailable
    state, v = vital_state(None, "BW")
    assert state == VITAL_STATE_UNAVAILABLE and v is None
    print("[OK] vital_state: None → unavailable")

    # missing
    state, v = vital_state({}, "BW")
    assert state == VITAL_STATE_MISSING and v is None
    state, v = vital_state({"BW": None}, "BW")
    assert state == VITAL_STATE_MISSING
    state, v = vital_state({"BW": ""}, "BW")
    assert state == VITAL_STATE_MISSING
    print("[OK] vital_state: 값 없음 → missing")

    # present
    state, v = vital_state({"BW": 18}, "BW")
    assert state == VITAL_STATE_PRESENT and v == 18.0
    state, v = vital_state({"BW": "18kg"}, "BW")
    assert state == VITAL_STATE_PRESENT and v == 18.0
    state, v = vital_state({"bw": 18}, "BW", "bw")       # 대소문자 매칭
    assert state == VITAL_STATE_PRESENT and v == 18.0
    state, v = vital_state({"BST": "123 mg/dL"}, "BST", "bst")
    assert state == VITAL_STATE_PRESENT and v == 123.0
    print("[OK] vital_state: 숫자 → present")

    # unknown
    state, v = vital_state({"BST": "?"}, "BST")
    assert state == VITAL_STATE_UNKNOWN
    state, v = vital_state({"BST": "uncertain"}, "BST")
    assert state == VITAL_STATE_UNKNOWN
    state, v = vital_state({"BST": float("nan")}, "BST")
    assert state == VITAL_STATE_UNKNOWN
    state, v = vital_state({"BST": {"status": "ocr_failed"}}, "BST")
    assert state == VITAL_STATE_UNKNOWN
    state, v = vital_state({"BST": "고혈당"}, "BST")    # 숫자 추출 실패 → UNKNOWN
    assert state == VITAL_STATE_UNKNOWN
    print("[OK] vital_state: 불확실 → unknown")

    # key 우선순위
    state, v = vital_state({"body_weight": 20, "BW": 18}, "BW", "body_weight")
    assert v == 18.0    # 첫 key 우선
    state, v = vital_state({"body_weight": 20}, "BW", "body_weight")
    assert v == 20.0    # fallback key
    print("[OK] vital_state: key 우선순위")

    # vitals_context 가 dict 아님 → TypeError
    try:
        vital_state("not a dict", "BW")
        raise AssertionError("문자열 vitals_context 가 통과")
    except TypeError:
        print("[OK] vitals_context 타입 강제")

    print("\n모든 self-test 통과.")
