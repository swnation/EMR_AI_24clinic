"""Session 5 tests for clinical_policy purpose."""

import pytest

from app.rules_v2.schema import (
    PURPOSE_CLINICAL_POLICY,
    SEVERITY_WARN,
    make_result,
)


def test_make_result_accepts_clinical_policy():
    """clinical_policy purpose 는 _VALID_PURPOSE 에 포함되어야 함."""
    r = make_result(
        rule_id="ped-iv-ban",
        purpose=PURPOSE_CLINICAL_POLICY,
        severity=SEVERITY_WARN,
        trigger="patient-context+order",
        message="만 12세 미만 소아 IV 수액은 원내 원칙상 제한",
        source="test",
    )
    assert r["purpose"] == "clinical_policy"
    assert r["severity"] == "warn"
    assert r["rule_id"] == "ped-iv-ban"
    assert r["level"] == "warn"


def test_clinical_policy_constant_value():
    """상수 값은 'clinical_policy' 문자열 고정."""
    assert PURPOSE_CLINICAL_POLICY == "clinical_policy"


def test_make_result_rejects_clinical_policy_typo():
    """'clinical-policy' 같은 오타는 거부."""
    with pytest.raises(ValueError, match="purpose"):
        make_result(
            rule_id="x",
            purpose="clinical-policy",
            severity=SEVERITY_WARN,
            trigger="order-only",
            message="m",
            source="test",
        )


def test_ped_iv_ban_result_shape():
    """마이그레이션된 ped-iv-ban rule 결과가 기대 스키마에 부합."""
    r = make_result(
        rule_id="ped-iv-ban",
        purpose=PURPOSE_CLINICAL_POLICY,
        severity=SEVERITY_WARN,
        trigger="patient-context+order",
        message="만 12세 미만 소아 IV 수액은 원내 원칙상 제한",
        sub=(
            "의학적 절대 금기가 아니라 24시열린의원 원내 운영 규칙. "
            "tamiiv(페라미플루 IV)도 IV 수액이므로 동일하게 제한 대상."
        ),
        source="rules.json v0.3 ped_iv_ban + 2026-04-25 붕쌤 정정",
        fallback_if_uncertain="unknown",
    )
    for key in (
        "rule_id",
        "purpose",
        "severity",
        "trigger",
        "fallback_if_uncertain",
        "level",
        "message",
        "sub",
        "source",
    ):
        assert key in r, f"필수 키 {key} 누락"
    assert r["level"] == "warn"
