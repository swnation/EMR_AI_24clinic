"""
Rules v2 공통 스키마 (v3 §8.4 Rule 기술 공통 형식 구현)

제공:
    - Severity: info / warn / unknown / hard
    - Purpose: safety / non_reversible_error / omission / format / history_conflict / clinical_policy
    - Trigger: dx-only / order-only / ... / vitals+order / 복합 + 가능
    - make_result(): 기존 checker.py 결과 dict 와 호환되는 RuleResult 생성 헬퍼

세션5 추가:
    - PURPOSE_CLINICAL_POLICY = "clinical_policy"
      의학적 절대 금기나 순수 청구 오류는 아니지만, 24시열린의원의 표준 진료·설명·운영 원칙상
      일관되게 안내하거나 확인해야 하는 항목. 예: ped_iv_ban, 향후 격리/등원/서류 안내.
"""
from typing import Any, Dict, Optional


# ─────────────────────────────────────────────────────────────
# Severity
# ─────────────────────────────────────────────────────────────
SEVERITY_INFO = "info"
SEVERITY_WARN = "warn"
SEVERITY_UNKNOWN = "unknown"
SEVERITY_HARD = "hard"

_VALID_SEVERITY = {SEVERITY_INFO, SEVERITY_WARN, SEVERITY_UNKNOWN, SEVERITY_HARD}


# ─────────────────────────────────────────────────────────────
# Purpose
# ─────────────────────────────────────────────────────────────
PURPOSE_SAFETY = "safety"
PURPOSE_NON_REVERSIBLE_ERROR = "non_reversible_error"
PURPOSE_OMISSION = "omission"
PURPOSE_FORMAT = "format"
PURPOSE_HISTORY_CONFLICT = "history_conflict"
PURPOSE_CLINICAL_POLICY = "clinical_policy"

_VALID_PURPOSE = {
    PURPOSE_SAFETY,
    PURPOSE_NON_REVERSIBLE_ERROR,
    PURPOSE_OMISSION,
    PURPOSE_FORMAT,
    PURPOSE_HISTORY_CONFLICT,
    PURPOSE_CLINICAL_POLICY,
}


# ─────────────────────────────────────────────────────────────
# Trigger
# ─────────────────────────────────────────────────────────────
_VALID_TRIGGER_ATOMIC = {
    "dx-only",
    "order-only",
    "dx+order",
    "special+order",
    "patient-context",
    "history-required",
    "vitals-only",
    "vitals+order",
}

_ALLOWED_COMPOSITE_TRIGGER_PIECES = {
    "dx",
    "order",
    "special",
    "vitals",
    "patient-context",
    "history-required",
}


# ─────────────────────────────────────────────────────────────
# Legacy level compatibility
# ─────────────────────────────────────────────────────────────
_SEVERITY_TO_LEGACY_LEVEL = {
    SEVERITY_HARD: "err",
    SEVERITY_WARN: "warn",
    SEVERITY_INFO: "info",
    SEVERITY_UNKNOWN: "unknown",
}


def _make_legacy_level(severity: str) -> str:
    """severity → 기존 checker.py level 호환 값."""
    return _SEVERITY_TO_LEGACY_LEVEL[severity]


# ─────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────
def _validate_trigger(trigger: str) -> None:
    """
    trigger 검증. 등록된 atomic 값이거나 '+' 로 결합된 복합 값이어야 한다.

    주의:
        'vitals', 'order', 'dx', 'special' 같은 단독 piece 는 reject.
        복합 값으로 쓸 때만 'patient-context+vitals+order' 처럼 결합한다.
    """
    if not isinstance(trigger, str) or not trigger:
        raise ValueError(f"trigger 는 비어있지 않은 문자열이어야 함. got: {trigger!r}")

    if trigger in _VALID_TRIGGER_ATOMIC:
        return

    if "+" not in trigger:
        raise ValueError(
            f"trigger {trigger!r} 는 등록된 atomic 값이 아님. "
            f"허용 atomic: {sorted(_VALID_TRIGGER_ATOMIC)}. "
            "복합 값이면 '+' 로 결합해야 함 (예: patient-context+vitals+order)."
        )

    for piece in trigger.split("+"):
        piece = piece.strip()
        if piece not in _ALLOWED_COMPOSITE_TRIGGER_PIECES:
            raise ValueError(
                f"trigger 조각 {piece!r} 이 허용 목록에 없음. "
                f"atomic 값: {sorted(_VALID_TRIGGER_ATOMIC)} / "
                f"복합 piece: {sorted(_ALLOWED_COMPOSITE_TRIGGER_PIECES)} / 입력: {trigger!r}"
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
        rule_id, purpose, severity, trigger, fallback_if_uncertain,
        level, message, sub, source, plus optional extra fields.
    """
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

    result: Dict[str, Any] = {
        "rule_id": rule_id,
        "purpose": purpose,
        "severity": severity,
        "trigger": trigger,
        "fallback_if_uncertain": fallback_if_uncertain,
        "level": _make_legacy_level(severity),
        "message": message,
        "sub": sub,
        "source": source,
    }

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


if __name__ == "__main__":
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
    assert r["level"] == "warn"
    assert r["fallback_if_uncertain"] == "unknown"
    print("[OK] 기본 생성")

    r = make_result(
        rule_id="test-2",
        purpose=PURPOSE_CLINICAL_POLICY,
        severity=SEVERITY_WARN,
        trigger="patient-context+order",
        message="clinical_policy 테스트",
    )
    assert r["purpose"] == "clinical_policy"
    assert r["level"] == "warn"
    print("[OK] clinical_policy purpose")

    for bad_purpose in ["unknown_purpose", "clinical-policy"]:
        try:
            make_result("x", bad_purpose, SEVERITY_WARN, "dx-only", "m")
            raise AssertionError(f"invalid purpose {bad_purpose!r} 가 통과함")
        except ValueError:
            pass
    print("[OK] invalid purpose 거부")

    for bare in ["vitals", "order", "dx", "special"]:
        try:
            make_result("x", PURPOSE_SAFETY, SEVERITY_WARN, bare, "m")
            raise AssertionError(f"단독 piece {bare!r} 가 통과함")
        except ValueError:
            pass
    print("[OK] 단독 piece 거부")

    print("\n모든 self-test 통과.")
