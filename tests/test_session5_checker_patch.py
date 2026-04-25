"""
test_session5_checker_patch.py
==============================

세션5 P0 patch 검증 — checker.py 의 hardcoded rule 3개가
v1 rules.json 결정과 일치하는지 확인.

검증 항목:
1. ped_iv_ban: tamiiv/tyiv 예외 없이 모든 IV 수액이 소아에게 warn 발동
2. tamiiv_info: 단순화된 문구 ("1회 투여로 완료" / "5일 연속 투여 아님")
3. dige_banned: 정리된 문구 + 시장 재승인 unpublish 안내

배치 위치:
    repo 의 tests/ 디렉토리에 그대로 추가.
    pytest 자동 발견.
"""
import pytest
from app.checker import run_check


# ═══════════════════════════════════════════════════════════════════
# Helper
# ═══════════════════════════════════════════════════════════════════
def _find_rule(results, message_contains: str):
    """results 에서 message 에 특정 문자열이 포함된 항목 찾기."""
    for r in results:
        if message_contains in r.get("message", ""):
            return r
    return None


# ═══════════════════════════════════════════════════════════════════
# ped_iv_ban — tamiiv/tyiv 예외 없음 검증 (가장 중요)
# ═══════════════════════════════════════════════════════════════════
class TestPedIvBan:
    """소아 IV 수액 제한 — 모든 IV 수액이 동일하게 발동."""

    def test_ped_general_iv_triggers_warn(self):
        """일반 IV 수액 (예: cefaiv 등) — 기본 케이스."""
        results = run_check(
            dx=["j209"],
            orders=["3cefaiv"],
            symptoms="기관지염",
            patient_type="소아",
        )
        rule = _find_rule(results, "만 12세 미만 소아 IV 수액")
        assert rule is not None, "소아에게 일반 IV 수액 처방 시 ped_iv_ban 발동되어야 함"
        assert rule["level"] == "warn", "clinical_policy → severity=warn"

    def test_ped_tamiiv_triggers_warn(self):
        """tamiiv 도 IV 수액. 소아에게 처방 시 발동되어야 함 (세션5 핵심 정정)."""
        results = run_check(
            dx=["j111"],
            orders=["tamiiv"],
            symptoms="독감",
            patient_type="소아",
        )
        rule = _find_rule(results, "만 12세 미만 소아 IV 수액")
        assert rule is not None, (
            "tamiiv 는 더 이상 ped_iv_ban 예외가 아님 (세션5 결정). "
            "소아에게 tamiiv 처방 시 반드시 warn 발동."
        )
        assert "tamiiv" in rule["sub"], "sub 문구에 모든 IV 수액 적용 안내 포함"

    def test_ped_tyiv_triggers_warn(self):
        """tyiv 도 IV 수액. 소아에게 처방 시 발동되어야 함 (세션5 GPT 2차 답변)."""
        results = run_check(
            dx=["j00"],
            orders=["tyiv"],
            symptoms="감기",
            patient_type="소아",
        )
        rule = _find_rule(results, "만 12세 미만 소아 IV 수액")
        assert rule is not None, (
            "tyiv 도 더 이상 ped_iv_ban 예외가 아님 (세션5 GPT 2차 답변). "
            "소아에게 tyiv 처방 시 반드시 warn 발동."
        )

    def test_adult_iv_no_warn(self):
        """성인에게는 IV 수액 처방해도 ped_iv_ban 발동 안 함."""
        results = run_check(
            dx=["j209"],
            orders=["3cefaiv"],
            symptoms="기관지염",
            patient_type="성인",
        )
        rule = _find_rule(results, "만 12세 미만 소아 IV 수액")
        assert rule is None, "성인에게는 ped_iv_ban 발동되지 않아야 함"

    def test_ped_oral_drug_no_warn(self):
        """소아여도 IV 가 아닌 약 (시럽 등) 은 ped_iv_ban 발동 안 함."""
        results = run_check(
            dx=["j209"],
            orders=["dropsy"],   # 시럽
            symptoms="기관지염",
            patient_type="소아",
        )
        rule = _find_rule(results, "만 12세 미만 소아 IV 수액")
        assert rule is None, "비-IV 약물에는 ped_iv_ban 발동되지 않아야 함"

    def test_message_matches_v1_rules_json(self):
        """v1 rules.json 의 message 와 일치 확인."""
        results = run_check(
            dx=["j111"],
            orders=["tamiiv"],
            symptoms="독감",
            patient_type="소아",
        )
        rule = _find_rule(results, "만 12세 미만 소아 IV 수액")
        assert rule["message"] == "만 12세 미만 소아 IV 수액은 원내 원칙상 제한"
        # sub 의 핵심 문구 검증
        assert "원내 운영 규칙" in rule["sub"]
        assert "tamiiv" in rule["sub"]
        assert "tyiv" in rule["sub"]


# ═══════════════════════════════════════════════════════════════════
# tamiiv_info — 단순화된 문구
# ═══════════════════════════════════════════════════════════════════
class TestTamiivInfo:
    """tamiiv 처방 시 1회 투여 안내."""

    def test_tamiiv_triggers_info(self):
        """성인에게 tamiiv 처방 시 info 발동."""
        results = run_check(
            dx=["j111"],
            orders=["tamiiv"],
            symptoms="독감",
            patient_type="성인",
        )
        rule = _find_rule(results, "1회 투여로 완료")
        assert rule is not None, "tamiiv 처방 시 단일 투여 안내 발동"
        assert rule["level"] == "info"

    def test_tamiiv_info_message_simplified(self):
        """문구가 v1 rules.json 과 일치 (단순화됨)."""
        results = run_check(
            dx=["j111"],
            orders=["tamiiv"],
            symptoms="독감",
            patient_type="성인",
        )
        rule = _find_rule(results, "1회 투여로 완료")
        assert rule["message"] == "tamiiv: 1회 투여로 완료"
        assert rule["sub"] == "5일 연속 투여 아님."


# ═══════════════════════════════════════════════════════════════════
# dige_banned — 정리된 문구
# ═══════════════════════════════════════════════════════════════════
class TestDigeBanned:
    """dige 시장 철수 안내."""

    def test_dige_triggers_warn(self):
        """dige 처방 시 warn 발동."""
        results = run_check(
            dx=["k299"],
            orders=["dige"],
            symptoms="위염",
            patient_type="성인",
        )
        rule = _find_rule(results, "dige 처방 불가")
        assert rule is not None
        assert rule["level"] == "warn"

    def test_dige_message_with_unpublish_note(self):
        """sub 에 시장 재승인 시 unpublish 안내 포함."""
        results = run_check(
            dx=["k299"],
            orders=["dige"],
            symptoms="위염",
            patient_type="성인",
        )
        rule = _find_rule(results, "dige 처방 불가")
        assert "ranitidine 국내 시장 철수" in rule["message"]
        assert "reba" in rule["sub"]
        assert "ppiiv" in rule["sub"]
        assert "시장 재승인 시 rule unpublish" in rule["sub"]


# ═══════════════════════════════════════════════════════════════════
# 통합 — 같은 케이스에 여러 rule 발동 시 대표 1건씩 모두 발동 확인
# ═══════════════════════════════════════════════════════════════════
class TestIntegration:
    """소아에게 tamiiv 처방 → ped_iv_ban + tamiiv_info 둘 다 발동."""

    def test_pediatric_tamiiv_triggers_both(self):
        results = run_check(
            dx=["j111"],
            orders=["tamiiv"],
            symptoms="독감",
            patient_type="소아",
        )
        # ped_iv_ban (warn)
        ped_rule = _find_rule(results, "만 12세 미만 소아 IV 수액")
        assert ped_rule is not None, "소아 + tamiiv → ped_iv_ban 발동"

        # tamiiv_info (info)
        info_rule = _find_rule(results, "1회 투여로 완료")
        assert info_rule is not None, "tamiiv 단일 투여 안내도 동시 발동"

        # 두 rule 의 severity 가 다르므로 별도 항목으로 결과에 들어가야 함
        assert ped_rule["level"] == "warn"
        assert info_rule["level"] == "info"
