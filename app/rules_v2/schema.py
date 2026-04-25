"""
Rules v2 공통 스키마 (v3 §8.4 Rule 기술 공통 형식 구현)

참조 문서:
    - design/system-overview-v3.md §8 (Rule 분류 체계)
    - decisions/decision-2026-04-21-capture-regions-and-rules.md §7 (Rule 기술 공통 형식)

제공:
    - Severity          : info / warn / unknown (v1 에서 hard 는 소아/BST rule 에 미사용)
    - Purpose           : safety / non_reversible_error / omission / format / history_conflict / clinical_policy
    - Trigger           : dx-only / order-only / ... / vitals+order / (복합 + 가능)
    - RuleResult        : rule 평가 1건 결과 (dict-like, 기존 checker.py 형식과 호환)
    - make_result()     : RuleResult 생성 헬퍼 (타입/enum 검증 포함)

설계 원칙:
    1. 기존 checker.py 의 결과 dict (level/message/sub/source) 와 필드 호환.
       - 신규 필드 (purpose/severity/trigger/fallback_if_uncertain/rule_id) 는
         기존 필드와 함께 나란히 들어감. 기존 UI 깨지 않음.
       - "level" 필드는 기존 호환용 alias. severity 와 같은 값.
         단 severity="unknown" 은 기존 level 체계에 없던 신규 카테고리 (v3 §7.5).
    2. Enum 값은 문자열 상수로. Python Enum 을 쓰지 않는 이유:
       - JSON 직렬화 단순 유지 (server.py → frontend JSON 전달).
       - Enum.value 접근 깜빡임 방지.
    3. 값 검증은 _VALID_* 집합에서. 오타 시 ValueError.
    4. unknown 은 severity 이자 fallback_if_uncertain 의 기본 반환값.
"""
from typing import Any, Dict, Optional


# ─────────────────────────────────────────────────────────────
# Enum 값 (문자열 상수)
# ─────────────────────────────────────────────────────────────

# v3 §7 등급 체계. v1 에서 hard 는 소아/BST rule 에서 사용 안 함.
SEVERITY_INFO = "info"
SEVERITY_WARN = "warn"
SEVERITY_UNKNOWN = "unknown"    # v3 §7.5 신규 카테고리 (OCR 불명확 등)
SEVERITY_HARD = "hard"          # 기존 시스템 호환용. Batch 1 rule 에서는 사용 안 함.

_VALID_SEVERITY = {SEVERITY_INFO, SEVERITY_WARN, SEVERITY_UNKNOWN, SEVERITY_HARD}


# v3 §8.1 목적축
PURPOSE_SAFETY = "safety"
PURPOSE_NON_REVERSIBLE_ERROR = "non_reversible_error"
PURPOSE_OMISSION = "omission"
PURPOSE_FORMAT = "format"
PURPOSE_HISTORY_CONFLICT = "history_conflict"
# session5: rules.json v1 마이그레이션에서 ped-iv-ban 등 원내 운영 규칙용으로 추가.
PURPOSE_CLINICAL_POLICY = "clinical_policy"

_VALID_PURPOSE = {
    PURPOSE_SAFETY, PURPOSE_NON_REVERSIBLE_ERROR,
    PURPOSE_OMISSION, PURPOSE_FORMAT, PURPOSE_HISTORY_CONFLICT,
    PURPOSE_CLINICAL_POLICY,
}


# v3 §8.2 트리거축. 복합 trigger 는 "+" 구분 허용 (예: patient-context+vitals+order)
# 여기서는 단일 atomic 값만 enum 으로 관리하고, make_result() 에서 "+" 분리 후 각 조각을 검증.
_VALID_TRIGGER_ATOMIC = {
    "dx-only", "order-only", "dx+order",           # dx+order 는 관습적으로 atomic 취급
    "special+order",
    "patient-context", "history-required",
    "vitals-only", "vitals+order",
}


# ─────────────────────────────────────────────────────────────
# 기존 checker.py level 필드와의 호환 매핑
# ─────────────────────────────────────────────────────────────
# 기존 checker.py 는 level 로 {err, warn, info, ok} 를 사용. 신규 체계는 severity.
# err 는 rules_v2 에서 hard 와 의미 겹침. 기존 UI 가 "err" 아이콘을 빨강으로 표시 중이므로
# 호환을 위해 severity=hard → level=err, 그 외는 severity 그대로.
#
# 이 매핑은 _make_legacy_level() 에서만 사용. rules_v2 외부에서 읽을 때 호환성 유지.
_SEVERITY_TO_LEGACY_LEVEL = {
    SEVERITY_HARD:    "err",
    SEVERITY_WARN:    "warn",
    SEVERITY_INFO:    "info",
    SEVERITY_UNKNOWN: "unknown",   # 기존 체계에 없음. UI 별도 처리 필요 (v3 §7.5).
}


def _make_legacy_level(severity: str) -> str:
    """severity → 기존 checker.py level 호환 값."""
    return _SEVERITY_TO_LEGACY_LEVEL[severity]


# ─────────────────────────────────────────────────────────────
# Trigger 복합 검증
# ─────────────────────────────────────────────────────────────
def _validate_trigger(trigger: str) -> None:
    """
    trigger 검증. atomic 값이거나 "+" 로 결합된 복합 값.
    복합 예: "patient-context+vitals+order".

    파싱 규칙:
        - "+" 로 split 한 각 조각이 _VALID_TRIGGER_ATOMIC 의 원소들의 "부분" 이어야 함.
        - 단, "dx+order", "vitals+order", "special+order" 는 atomic 자체가 "+" 를 포함.
          → atomic 매칭을 먼저 시도, 실패 시 + 분해.

    구현: 가장 단순하게, trigger 전체가 atomic 에 있거나,
          + 로 분해한 모든 piece 가 {dx, order, special, vitals, patient-context, history-required}
          의 재조합으로 해석 가능하면 통과.
    """
    if not isinstance(trigger, str) or not trigger:
        raise ValueError(f"trigger 는 비어있지 않은 문자열이어야 함. got: {trigger!r}")

    # 1) atomic 매칭 먼저
    if trigger in _VALID_TRIGGER_ATOMIC:
        return

    # 2) atomic 도 아니고 "+" 없는 단독 문자열 → reject.
    #    (GPT redline #4, 2026-04-24): 과거 "vitals" 같은 단독 piece 가 의도치 않게
    #    통과하던 버그 차단. 단독은 반드시 _VALID_TRIGGER_ATOMIC 에 등록된 값이어야 함.
    if "+" not in trigger:
        raise ValueError(
            f"trigger {trigger!r} 는 등록된 atomic 값이 아님. "
            f"허용 atomic: {sorted(_VALID_TRIGGER_ATOMIC)}. "
            f"복합 값이면 '+' 로 결합해야 함 (예: patient-context+vitals+order)."
        )

    # 3) 복합 분해 — "+" 로 나눈 각 조각이 허용 piece 이어야 함.
    #    허용 piece = atomic 내부에 등장하는 단어들.
    allowed_pieces = {
        "dx", "order", "special", "vitals",
        "patient-context", "history-required",
        # "-only" 접미사는 단일 piece 복합일 때는 사용하지 않음.
    }
    pieces = trigger.split("+")
    for p in pieces:
        p = p.strip()
        if p not in allowed_pieces:
            raise ValueError(
                f"trigger 조각 {p!r} 이 허용 목록에 없음. "
                f"atomic 값: {sorted(_VALID_TRIGGER_ATOMIC)} / "
                f"복합 piece: {sorted(allowed_pieces)} / 입력: {trigger!r}"
            )


# ─────────────────────────────────────────────────────────────
# RuleResult 생성
# ─────────────────────────────────────────────────────────────
def make_result(
    rule_id: str,
    purpose: str,
    severity: str,
    trigger: str,
    message: str,
    sub: str = "",
    source: str = "",
    fallback_if_uncertain: str = SEVERITY_UNKNOWN,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Rule 평가 1건 결과 dict 생성. 기존 checker.py 결과 dict 와 호환.

    반환 키:
        - rule_id               (신규)
        - purpose               (신규)
        - severity              (신규, v3 §8.4)
        - trigger               (신규, v3 §8.2)
        - fallback_if_uncertain (신규, v3 §8.4)
        - level                 (기존 호환, severity → legacy 매핑)
        - message, sub, source  (기존 호환)

    검증:
        - severity, purpose, fallback_if_uncertain → enum 검증
        - trigger → atomic or 복합 piece 검증
        - rule_id, message → 비어있지 않은 str
        - extra → Optional dict. 있으면 merge 되며, 예약 키 (위 키 목록) 는 덮어쓸 수 없음.
    """
    # ── 타입/enum 검증 ──
    if not isinstance(rule_id, str) or not rule_id.strip():
        raise ValueError(f"rule_id 는 비어있지 않은 문자열이어야 함. got: {rule_id!r}")

    if purpose not in _VALID_PURPOSE:
        raise ValueError(
            f"purpose {purpose!r} 는 허용 값이 아님. 허용: {sorted(_VALID_PURPOSE)}"
        )

    if severity not in _VALID_SEVERITY:
        raise ValueError(
            f"severity {severity!r} 는 허용 값이 아님. 허용: {sorted(_VALID_SEVERITY)}"
        )

    if fallback_if_uncertain not in _VALID_SEVERITY:
        raise ValueError(
            f"fallback_if_uncertain {fallback_if_uncertain!r} 는 허용 값이 아님. "
            f"허용: {sorted(_VALID_SEVERITY)}"
        )

    _validate_trigger(trigger)

    if not isinstance(message, str) or not message.strip():
        raise ValueError(f"message 는 비어있지 않은 문자열이어야 함. got: {message!r}")

    if not isinstance(sub, str):
        raise ValueError(f"sub 는 문자열이어야 함. got: {type(sub).__name__}")

    if not isinstance(source, str):
        raise ValueError(f"source 는 문자열이어야 함. got: {type(source).__name__}")

    result = {
        "rule_id": rule_id,
        "purpose": purpose,
        "severity": severity,
        "trigger": trigger,
        "fallback_if_uncertain": fallback_if_uncertain,
        "level": _make_legacy_level(severity),   # 기존 UI 호환
        "message": message,
        "sub": sub,
        "source": source,
    }

    # ── extra merge (예약 키 충돌 금지) ──
    if extra is not None:
        if not isinstance(extra, dict):
            raise TypeError(f"extra 는 dict 여야 함. got: {type(extra).__name__}")
        reserved = set(result.keys())
        conflict = reserved & set(extra.keys())
        if conflict:
            raise ValueError(
                f"extra 에 예약된 키가 들어있음: {sorted(conflict)}. "
                "rule_id/purpose/severity/trigger/level/message/sub/source/fallback_if_uncertain "
                "은 make_result 고정 파라미터로만 전달해야 함."
            )
        result.update(extra)

    return result


# ─────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # 기본 생성
    r = make_result(
        rule_id="test-1",
        purpose=PURPOSE_NON_REVERSIBLE_ERROR,
        severity=SEVERITY_WARN,
        trigger="vitals+order",
        message="테스트 메시지",
        sub="부가 설명",
        source="test",
    )
    assert r["rule_id"] == "test-1"
    assert r["severity"] == "warn"
    assert r["level"] == "warn"         # 기존 호환
    assert r["fallback_if_uncertain"] == "unknown"
    print("[OK] 기본 생성")

    # 복합 trigger
    r = make_result(
        rule_id="test-2",
        purpose=PURPOSE_SAFETY,
        severity=SEVERITY_INFO,
        trigger="patient-context+vitals+order",
        message="복합 trigger 테스트",
    )
    assert r["trigger"] == "patient-context+vitals+order"
    print("[OK] 복합 trigger")

    # unknown severity 반환 → level 도 unknown
    r = make_result(
        rule_id="test-3",
        purpose=PURPOSE_OMISSION,
        severity=SEVERITY_UNKNOWN,
        trigger="vitals+order",
        message="OCR 불명확",
    )
    assert r["severity"] == "unknown"
    assert r["level"] == "unknown"
    print("[OK] unknown severity")

    # hard → level=err 호환 매핑
    r = make_result(
        rule_id="test-4",
        purpose=PURPOSE_SAFETY,
        severity=SEVERITY_HARD,
        trigger="dx+order",
        message="hard 매핑 테스트",
    )
    assert r["level"] == "err"
    print("[OK] hard → err 호환 매핑")

    # extra 추가
    r = make_result(
        rule_id="test-5",
        purpose=PURPOSE_SAFETY,
        severity=SEVERITY_WARN,
        trigger="order-only",
        message="extra 포함",
        extra={"matched_code": "umk", "dose_given": 25.0},
    )
    assert r["matched_code"] == "umk"
    assert r["dose_given"] == 25.0
    print("[OK] extra merge")

    # clinical_policy purpose (session5: ped-iv-ban 용)
    r = make_result(
        rule_id="ped-iv-ban",
        purpose=PURPOSE_CLINICAL_POLICY,
        severity=SEVERITY_WARN,
        trigger="patient-context+order",
        message="만 12세 미만 소아 IV 수액은 원내 원칙상 제한",
    )
    assert r["purpose"] == "clinical_policy"
    print("[OK] clinical_policy purpose")

    # ── 실패 케이스 ──
    try:
        make_result("x", "unknown_purpose", SEVERITY_WARN, "dx-only", "m")
        raise AssertionError("invalid purpose 가 통과함")
    except ValueError:
        print("[OK] invalid purpose 거부")

    try:
        make_result("x", PURPOSE_SAFETY, "emergency", "dx-only", "m")
        raise AssertionError("invalid severity 가 통과함")
    except ValueError:
        print("[OK] invalid severity 거부")

    try:
        make_result("x", PURPOSE_SAFETY, SEVERITY_WARN, "invalid-trigger", "m")
        raise AssertionError("invalid trigger 가 통과함")
    except ValueError:
        print("[OK] invalid trigger 거부")

    try:
        make_result("x", PURPOSE_SAFETY, SEVERITY_WARN, "weird+stuff", "m")
        raise AssertionError("invalid 복합 piece 가 통과함")
    except ValueError:
        print("[OK] invalid 복합 piece 거부")

    # 단독 piece reject (GPT redline #4, 2026-04-24)
    for bare in ["vitals", "order", "dx", "special"]:
        try:
            make_result("x", PURPOSE_SAFETY, SEVERITY_WARN, bare, "m")
            raise AssertionError(f"단독 piece {bare!r} 가 통과함")
        except ValueError:
            pass
    print("[OK] 단독 piece (vitals/order/dx/special) 거부")

    try:
        make_result("", PURPOSE_SAFETY, SEVERITY_WARN, "dx-only", "m")
        raise AssertionError("빈 rule_id 가 통과함")
    except ValueError:
        print("[OK] 빈 rule_id 거부")

    try:
        make_result("x", PURPOSE_SAFETY, SEVERITY_WARN, "dx-only", "")
        raise AssertionError("빈 message 가 통과함")
    except ValueError:
        print("[OK] 빈 message 거부")

    try:
        make_result(
            "x", PURPOSE_SAFETY, SEVERITY_WARN, "dx-only", "m",
            extra={"rule_id": "hack"},
        )
        raise AssertionError("extra 로 예약 키 덮어쓰기 통과함")
    except ValueError:
        print("[OK] 예약 키 충돌 거부")

    print("\n모든 self-test 통과.")
