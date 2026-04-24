"""
BST rule — 값↔코드 짝짓기 양방향 (v3 §8.5.2 / §8.5.3)

참조 문서:
    - design/system-overview-v3.md §8.5.2 / §8.5.3
    - decisions/decision-2026-04-21-capture-regions-and-rules.md §6

Rules:
    - Rule-BST-1 (bst-code-missing)   : BST 값 있음 + 'bst' 코드 없음
      purpose=non_reversible_error, severity=warn, trigger=vitals+order
      → 사후 청구 수정 어려움.

    - Rule-BST-2 (bst-value-missing)  : 'bst' 코드 있음 + BST 값 없음
      purpose=omission, severity=warn, trigger=vitals+order
      → 차트 완결성 문제. 측정값 보완 필요.

OCR 불명확 처리 (v3 §7.5 / Decision D3 §6):
    둘 중 하나라도 OCR/파싱 불명확 → 즉시 단정하지 않고 severity=unknown.
    조용한 skip 금지.

    예외: vitals_context 자체가 None (legacy pipeline 미연결) → rule 전체 skip.
    이유: parser/server 가 vitals_context 를 넘기지 않는 구버전 호출 호환.
    v3 §7.5 의 "조용한 skip 금지" 원칙과 충돌하지만, backward-compat 한정
    명시적 예외. 운영 로그는 호출측 (checker.py) 에서 1회/세션 남김.

청구 원칙과의 관계 (v3 §6.2):
    Rule-BST-1 은 "청구 자동화" 가 아니라 "되돌리기 어려운 실수" 로 분류.
    decision-2026-04-19 의 청구 rule 제외 원칙과 충돌 없음.

입력 계약:
    vitals_context:
        None  → 파이프라인 미연결. rule 전체 skip (빈 리스트 반환).
        dict  → 각 key 에서 BST 값을 읽음. OCR 노이즈는 vitals_utils 가 정규화.

    orders:
        None                   → orders 전체 OCR 실패 → unknown 결과 1건.
        set/list/tuple[str]    → 정규화된 코드 목록.

    BST 오더 코드:
        확정 값 "bst" (소문자, 2026-04-24 붕쌤 확인).
        변경 시 BST_ORDER_CODE 상수 한 곳만.
"""
from typing import Any, Dict, Iterable, List, Optional

from app.rules_v2.schema import (
    PURPOSE_NON_REVERSIBLE_ERROR,
    PURPOSE_OMISSION,
    SEVERITY_UNKNOWN,
    SEVERITY_WARN,
    make_result,
)
from app.rules_v2.vitals_utils import (
    VITAL_STATE_MISSING,
    VITAL_STATE_PRESENT,
    VITAL_STATE_UNAVAILABLE,
    VITAL_STATE_UNKNOWN,
    vital_state,
)


# ─────────────────────────────────────────────────────────────
# 고정 상수
# ─────────────────────────────────────────────────────────────
BST_ORDER_CODE = "bst"      # 2026-04-24 확정. 소문자. 변경 시 여기 한 곳만.
_SOURCE = "v3 §8.5.2/§8.5.3"


# ─────────────────────────────────────────────────────────────
# 내부 헬퍼
# ─────────────────────────────────────────────────────────────
def _orders_state(orders: Any) -> str:
    """
    orders 의 상태 분류.

    반환:
        "unknown"  → None (OCR 실패 / 정보 없음).
        "ready"    → list/set/tuple (빈 것 포함) — 정상 조회 가능.
    """
    if orders is None:
        return "unknown"
    if isinstance(orders, (list, set, tuple, frozenset)):
        return "ready"
    raise ValueError(
        f"orders 타입 지원 안 됨: {type(orders).__name__}. "
        "None 또는 list/set/tuple 이어야 함."
    )


def _has_bst_code(orders: Iterable[str]) -> bool:
    """
    orders 에 BST_ORDER_CODE 가 있는지. 방어적 정규화 포함.
    """
    for code in orders:
        if not isinstance(code, str):
            continue
        if code.strip().lower() == BST_ORDER_CODE:
            return True
    return False


# ─────────────────────────────────────────────────────────────
# Public: Rule 평가 진입점
# ─────────────────────────────────────────────────────────────
def check_bst_rules(
    vitals_context: Optional[dict],
    orders: Optional[Iterable[str]],
) -> List[Dict[str, Any]]:
    """
    BST 양방향 rule 평가. 0~2개의 RuleResult 반환.

    동작:
        0. vitals_context 자체가 None → rule 전체 skip (legacy backward-compat).
        1. 각 입력 상태 분류.
        2. 둘 중 하나라도 uncertain 이면 unknown 결과 1건 반환하고 끝.
        3. 양쪽 모두 확정 가능하면 두 rule 조건 검사.

    반환:
        rule 결과 dict 리스트. 발동 안 한 경우 빈 리스트.
    """
    # ── [0] vitals_context 미연결 → 전체 skip ──
    if vitals_context is None:
        return []

    # ── [1] 상태 분류 ──
    state, bst_value = vital_state(vitals_context, "BST", "bst", "blood_glucose")
    o_state = _orders_state(orders)

    if state == VITAL_STATE_UNAVAILABLE:
        # 위 short-circuit 에서 잡아야 하는데 방어적 branch. 로직상 도달 불가.
        return []

    # ── [2] 불명확 상태 통합 처리 ──
    if state == VITAL_STATE_UNKNOWN or o_state == "unknown":
        return [make_result(
            rule_id="bst-ocr-uncertain",
            purpose=PURPOSE_NON_REVERSIBLE_ERROR,   # 잠재 리스크 쪽으로 보수적 분류
            severity=SEVERITY_UNKNOWN,
            trigger="vitals+order",
            message="BST 값 또는 오더 코드 OCR/파싱 불명확 — 수기 확인 필요",
            sub=f"BST 상태={state}, orders 상태={o_state}",
            source=_SOURCE,
            fallback_if_uncertain=SEVERITY_UNKNOWN,
        )]

    # 여기서부터 state ∈ {PRESENT, MISSING}, o_state == "ready" 확정.
    has_code = _has_bst_code(orders)
    results: List[Dict[str, Any]] = []

    # ── Rule-BST-1: BST 값 있음 + 코드 없음 ──
    if state == VITAL_STATE_PRESENT and not has_code:
        results.append(make_result(
            rule_id="bst-code-missing",
            purpose=PURPOSE_NON_REVERSIBLE_ERROR,
            severity=SEVERITY_WARN,
            trigger="vitals+order",
            message=f"BST 값({bst_value:g}) 기록 있음 + '{BST_ORDER_CODE}' 오더 코드 누락",
            sub="사후 청구 수정 어려움. 오더에 BST 코드 추가 필요.",
            source=_SOURCE,
            fallback_if_uncertain=SEVERITY_UNKNOWN,
            extra={"bst_value": bst_value},
        ))

    # ── Rule-BST-2: 코드 있음 + BST 값 없음 ──
    if state == VITAL_STATE_MISSING and has_code:
        results.append(make_result(
            rule_id="bst-value-missing",
            purpose=PURPOSE_OMISSION,
            severity=SEVERITY_WARN,
            trigger="vitals+order",
            message=f"'{BST_ORDER_CODE}' 오더 있음 + BST 측정값 누락",
            sub="차트 완결성 문제. 측정값 보완 필요.",
            source=_SOURCE,
            fallback_if_uncertain=SEVERITY_UNKNOWN,
        ))

    return results


# ─────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # ── legacy pipeline (vitals_context=None) → 전체 skip ──
    r = check_bst_rules(vitals_context=None, orders=["bst"])
    assert r == []
    r = check_bst_rules(vitals_context=None, orders=[])
    assert r == []
    print("[OK] vitals_context None → rule 전체 skip (legacy backward-compat)")

    # ── 둘 다 정상 (이상 없음) ──
    r = check_bst_rules(vitals_context={"BST": 120}, orders={"bst", "loxo"})
    assert r == []
    r = check_bst_rules(vitals_context={"BST": None}, orders={"loxo"})
    assert r == []
    print("[OK] 정상 케이스 (결과 없음)")

    # ── Rule-BST-1: 값 있음 + 코드 없음 ──
    r = check_bst_rules(vitals_context={"BST": 180}, orders={"loxo", "aug2"})
    assert len(r) == 1
    assert r[0]["rule_id"] == "bst-code-missing"
    assert r[0]["severity"] == "warn"
    assert r[0]["purpose"] == "non_reversible_error"
    assert r[0]["bst_value"] == 180.0
    print("[OK] Rule-BST-1 발동")

    # ── OCR 문자열에서 숫자 추출 ──
    r = check_bst_rules(vitals_context={"BST": "180 mg/dL"}, orders={"loxo"})
    assert len(r) == 1 and r[0]["rule_id"] == "bst-code-missing"
    assert r[0]["bst_value"] == 180.0
    print("[OK] Rule-BST-1 with OCR-noisy value")

    # ── Rule-BST-2: 코드 있음 + 값 없음 ──
    r = check_bst_rules(vitals_context={"BST": None}, orders={"bst", "loxo"})
    assert len(r) == 1
    assert r[0]["rule_id"] == "bst-value-missing"
    assert r[0]["severity"] == "warn"
    assert r[0]["purpose"] == "omission"
    print("[OK] Rule-BST-2 발동")

    # ── 빈 문자열도 missing 으로 ──
    r = check_bst_rules(vitals_context={"BST": ""}, orders={"bst"})
    assert len(r) == 1 and r[0]["rule_id"] == "bst-value-missing"
    print("[OK] 빈 문자열 BST → Rule-BST-2")

    # ── 둘 다 있음 (정상) ──
    r = check_bst_rules(vitals_context={"BST": 95}, orders={"bst"})
    assert r == []
    print("[OK] 값+코드 모두 있음 → 통과")

    # ── Uncertain: "?", dict status, NaN 다양 형태 ──
    for unknown_form in ["?", "uncertain", "ocr_failed", "??",
                         float("nan"), {"status": "unknown"}, {"uncertain": True}]:
        r = check_bst_rules(vitals_context={"BST": unknown_form}, orders={"bst"})
        assert len(r) == 1 and r[0]["severity"] == "unknown", \
            f"unknown form {unknown_form!r} 가 unknown 으로 잡히지 않음: {r}"
    print("[OK] 다양한 uncertain 형태 → unknown 결과")

    # ── orders None → unknown ──
    r = check_bst_rules(vitals_context={"BST": 150}, orders=None)
    assert len(r) == 1 and r[0]["severity"] == "unknown"
    print("[OK] orders None → unknown 결과")

    # ── 대소문자/공백 섞인 코드 정규화 ──
    r = check_bst_rules(vitals_context={"BST": None}, orders={" BST ", "loxo"})
    assert len(r) == 1 and r[0]["rule_id"] == "bst-value-missing"
    print("[OK] 대소문자/공백 섞인 코드 정규화")

    # ── key 대소문자: "bst" 소문자 읽기도 OK ──
    r = check_bst_rules(vitals_context={"bst": 200}, orders={"loxo"})
    assert len(r) == 1 and r[0]["rule_id"] == "bst-code-missing"
    print("[OK] vitals_context 키 대소문자 무시")

    # ── 실패 케이스 ──
    try:
        check_bst_rules(vitals_context={"BST": 100}, orders="bst")
        raise AssertionError("str orders 가 통과함")
    except ValueError:
        print("[OK] str orders 거부")

    try:
        check_bst_rules(vitals_context="not a dict", orders=["bst"])
        raise AssertionError("str vitals_context 가 통과")
    except TypeError:
        print("[OK] str vitals_context 거부")

    print("\n모든 self-test 통과.")
