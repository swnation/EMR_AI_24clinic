"""
Pytest suite for rules_v2 (session 4).

실행:
    cd <repo root>
    pytest -q tests/test_rules_v2.py

커버리지:
    - schema.make_result validation
    - age_utils.is_age_minor_under_12
    - vitals_utils.coerce_float / is_unknown_value / vital_state
    - bst.check_bst_rules (Rule-BST-1, Rule-BST-2, uncertain)
    - pediatric_dose.check_pediatric_formulation_dose
        - weight_bracket_fixed (tysy)
        - age_bracket_fixed (umk)
        - hospital_daily_cap_only (augsy)
        - needs_review (suda2)
        - BW 없음/불확실 처리
        - 의학적 최대 초과 vs 원내 상한 초과 분기
"""
import pytest

from app.rules_v2.age_utils import is_age_minor_under_12
from app.rules_v2.bst import check_bst_rules
from app.rules_v2.pediatric_dose import (
    check_pediatric_formulation_dose,
    load_pediatric_drug_list,
)
from app.rules_v2.schema import (
    PURPOSE_CLINICAL_POLICY,
    PURPOSE_NON_REVERSIBLE_ERROR,
    PURPOSE_OMISSION,
    PURPOSE_SAFETY,
    SEVERITY_INFO,
    SEVERITY_UNKNOWN,
    SEVERITY_WARN,
    make_result,
)
from app.rules_v2.vitals_utils import (
    VITAL_STATE_MISSING,
    VITAL_STATE_PRESENT,
    VITAL_STATE_UNAVAILABLE,
    VITAL_STATE_UNKNOWN,
    coerce_float,
    is_unknown_value,
    vital_state,
)


# ───────────────────────── fixtures ─────────────────────────
@pytest.fixture
def tysy_only_drug_list():
    """tysy 만 등록된 최소 curated list."""
    return {
        "drugs": {
            "tysy": {
                "name": "세토펜현탁액",
                "ingredient": "acetaminophen",
                "formulation": "syrup",
                "concentration_mg_per_ml": 32.0,
                "unit": "mL",
                "typical_freq_per_day": 3,
                "dosing_rule_type": "weight_bracket_fixed",
                "weight_brackets": [
                    {"weight_kg_min": 12, "weight_kg_max": 15.9, "per_dose_ml": 5.0},
                    {"weight_kg_min": 16, "weight_kg_max": 22.9, "per_dose_ml": 7.5},
                ],
                "tolerance_pct": 15,
                "medical_max_mg_per_kg_per_day": 75,
            },
        }
    }


@pytest.fixture
def augsy_only_drug_list():
    """augsy 만 등록된 최소 curated list (실제 농도 40 mg/mL)."""
    return {
        "drugs": {
            "augsy": {
                "name": "하이크라듀오",
                "ingredient": "amoxicillin-clavulanate",
                "formulation": "syrup",
                "concentration_mg_per_ml": 40.0,
                "unit": "mL",
                "typical_freq_per_day": 3,
                "dosing_rule_type": "hospital_daily_cap_only",
                "hospital_recommended_daily_max_ml": 30,
                "medical_max_mg_per_kg_per_day": 90,
                "alternative_if_over_hospital_cap": "aug 알약",
            },
        }
    }


@pytest.fixture
def umk_only_drug_list():
    """umk 만 등록된 curated list (나이 기반 고정)."""
    return {
        "drugs": {
            "umk": {
                "name": "움카민",
                "formulation": "syrup",
                "unit": "mL",
                "typical_freq_per_day": 3,
                "dosing_rule_type": "age_bracket_fixed",
                "age_brackets": {
                    "2~6세":  {"daily_total_ml": 9,  "per_dose_ml": 3},
                    "6~9세":  {"daily_total_ml": 18, "per_dose_ml": 6},
                    "9~10세": {"daily_total_ml": 18, "per_dose_ml": 6},
                },
                "tolerance_pct": 0,
            }
        }
    }


# ───────────────────────── schema ─────────────────────────
class TestSchema:
    def test_make_result_minimal_required_fields(self):
        r = make_result(
            rule_id="x", purpose=PURPOSE_SAFETY,
            severity=SEVERITY_INFO, trigger="vitals-only",
            message="m", source="s",
        )
        # legacy 호환 (level 매핑 존재)
        assert r["severity"] == "info"
        assert r["level"] == "info"

    def test_make_result_invalid_severity_raises(self):
        with pytest.raises(ValueError):
            make_result(
                rule_id="x", purpose=PURPOSE_SAFETY,
                severity="BAD", trigger="vitals-only",
                message="m", source="s",
            )

    @pytest.mark.parametrize("bare_piece", ["vitals", "order", "dx", "special"])
    def test_bare_piece_trigger_rejected(self, bare_piece):
        # GPT redline #4 (2026-04-24): atomic 아닌 단독 piece 는 reject.
        # 과거엔 "vitals" 가 통과하는 버그 있었음.
        with pytest.raises(ValueError):
            make_result(
                rule_id="x", purpose=PURPOSE_SAFETY,
                severity=SEVERITY_INFO, trigger=bare_piece,
                message="m", source="s",
            )

    def test_valid_composite_trigger(self):
        # 복합 trigger 는 여전히 허용.
        r = make_result(
            rule_id="x", purpose=PURPOSE_SAFETY,
            severity=SEVERITY_INFO,
            trigger="patient-context+vitals+order",
            message="m", source="s",
        )
        assert r["trigger"] == "patient-context+vitals+order"

    def test_clinical_policy_purpose_accepted(self):
        # session5: rules.json v1 의 ped-iv-ban 등 원내 운영 규칙 카테고리.
        r = make_result(
            rule_id="ped-iv-ban",
            purpose=PURPOSE_CLINICAL_POLICY,
            severity=SEVERITY_WARN,
            trigger="patient-context+order",
            message="만 12세 미만 소아 IV 수액은 원내 원칙상 제한",
            source="rules.json v0.3 ped_iv_ban + 2026-04-25 붕쌤 정정",
        )
        assert r["purpose"] == "clinical_policy"
        assert r["severity"] == "warn"
        assert r["level"] == "warn"


# ───────────────────────── age_utils ─────────────────────────
class TestAgeUtils:
    def test_under_12_from_age_minor(self):
        assert is_age_minor_under_12(age_minor="2~6세") is True
        assert is_age_minor_under_12(age_minor="6~9세") is True
        assert is_age_minor_under_12(age_minor="10~12세") is True

    def test_over_12_from_age_minor(self):
        # 16구간에서 12세 이상 구간.
        assert is_age_minor_under_12(age_minor="12~15세") is False

    def test_from_age_years(self):
        assert is_age_minor_under_12(age_years=5) is True
        assert is_age_minor_under_12(age_years=11) is True
        assert is_age_minor_under_12(age_years=12) is False
        assert is_age_minor_under_12(age_years=30) is False

    def test_completely_missing_returns_none(self):
        assert is_age_minor_under_12(age_minor=None, age_years=None) is None


# ───────────────────────── vitals_utils ─────────────────────────
class TestCoerceFloat:
    def test_ocr_noisy_strings(self):
        assert coerce_float("18kg") == 18.0
        assert coerce_float("BST 123") == 123.0
        assert coerce_float("37.4 mg/dL") == 37.4

    def test_unknown_sentinels_return_none(self):
        assert coerce_float("?") is None
        assert coerce_float("uncertain") is None
        assert coerce_float("") is None

    def test_nan_inf_return_none(self):
        assert coerce_float(float("nan")) is None
        assert coerce_float(float("inf")) is None

    def test_bool_rejected(self):
        with pytest.raises(TypeError):
            coerce_float(True)

    def test_dict_not_recursed(self):
        # 내 구현은 dict 재귀 탐색 안 함. GPT 원본과 차이점.
        assert coerce_float({"value": 18}) is None

    def test_decimal_comma(self):
        # GPT redline #1 (2026-04-24): "5,0" European decimal → 5.0, 50.0 아님.
        assert coerce_float("5,0") == 5.0
        assert coerce_float("12,5") == 12.5
        assert coerce_float("12,5kg") == 12.5
        assert coerce_float("37,4") == 37.4
        assert coerce_float("-3,5") == -3.5

    def test_thousand_separator(self):
        # 천단위 구분 쉼표는 제거.
        assert coerce_float("1,234") == 1234.0
        assert coerce_float("12,345") == 12345.0

    def test_thousand_plus_decimal(self):
        # 천단위 + 소수점 혼합.
        assert coerce_float("1,234.5") == 1234.5


class TestIsUnknownValue:
    def test_none_is_not_unknown(self):
        # None 은 MISSING 이지 UNKNOWN 아님.
        assert is_unknown_value(None) is False

    def test_unknown_strings(self):
        assert is_unknown_value("?") is True
        assert is_unknown_value("UNCERTAIN") is True
        assert is_unknown_value("ocr_failed") is True

    def test_dict_status(self):
        assert is_unknown_value({"status": "unknown"}) is True
        assert is_unknown_value({"uncertain": True}) is True

    def test_nan(self):
        assert is_unknown_value(float("nan")) is True

    def test_valid_number_is_not_unknown(self):
        assert is_unknown_value(120) is False
        assert is_unknown_value(37.4) is False


class TestVitalState:
    def test_none_is_unavailable(self):
        state, v = vital_state(None, "BW")
        assert state == VITAL_STATE_UNAVAILABLE
        assert v is None

    def test_missing_values(self):
        for val in [{}, {"BW": None}, {"BW": ""}]:
            state, v = vital_state(val, "BW")
            assert state == VITAL_STATE_MISSING

    def test_present_values(self):
        state, v = vital_state({"BW": 18}, "BW")
        assert state == VITAL_STATE_PRESENT and v == 18.0

    def test_ocr_noisy_present(self):
        state, v = vital_state({"BST": "123 mg/dL"}, "BST")
        assert state == VITAL_STATE_PRESENT and v == 123.0

    def test_uncertain_values(self):
        for val in ["?", "uncertain", float("nan"), {"status": "ocr_failed"}]:
            state, _ = vital_state({"BST": val}, "BST")
            assert state == VITAL_STATE_UNKNOWN, f"failed for {val!r}"

    def test_key_priority(self):
        state, v = vital_state({"body_weight": 20, "BW": 18}, "BW", "body_weight")
        assert v == 18.0

    def test_key_fallback(self):
        state, v = vital_state({"body_weight": 20}, "BW", "body_weight")
        assert v == 20.0


# ───────────────────────── BST rules ─────────────────────────
class TestBstRules:
    def test_none_vitals_skips_all(self):
        # Legacy backward-compat: vitals_context 미연결 → 전체 skip.
        assert check_bst_rules(None, ["bst"]) == []
        assert check_bst_rules(None, []) == []

    def test_rule_bst_1_value_without_code(self):
        r = check_bst_rules({"BST": 180}, ["loxo"])
        assert len(r) == 1
        assert r[0]["rule_id"] == "bst-code-missing"
        assert r[0]["severity"] == SEVERITY_WARN
        assert r[0]["purpose"] == PURPOSE_NON_REVERSIBLE_ERROR

    def test_rule_bst_1_with_ocr_noisy_value(self):
        r = check_bst_rules({"BST": "180 mg/dL"}, ["loxo"])
        assert len(r) == 1
        assert r[0]["rule_id"] == "bst-code-missing"
        assert r[0]["bst_value"] == 180.0

    def test_rule_bst_2_code_without_value(self):
        r = check_bst_rules({"BST": None}, ["bst"])
        assert len(r) == 1
        assert r[0]["rule_id"] == "bst-value-missing"
        assert r[0]["severity"] == SEVERITY_WARN
        assert r[0]["purpose"] == PURPOSE_OMISSION

    def test_both_present_no_alert(self):
        assert check_bst_rules({"BST": 95}, ["bst"]) == []

    def test_both_absent_no_alert(self):
        assert check_bst_rules({"BST": None}, ["loxo"]) == []

    @pytest.mark.parametrize("uncertain_form", [
        "?", "uncertain", "ocr_failed", float("nan"),
        {"status": "unknown"}, {"uncertain": True},
    ])
    def test_uncertain_values_produce_unknown(self, uncertain_form):
        r = check_bst_rules({"BST": uncertain_form}, ["bst"])
        assert len(r) == 1 and r[0]["severity"] == SEVERITY_UNKNOWN
        assert r[0]["rule_id"] == "bst-ocr-uncertain"

    def test_orders_none_is_unknown(self):
        r = check_bst_rules({"BST": 150}, None)
        assert len(r) == 1 and r[0]["severity"] == SEVERITY_UNKNOWN

    def test_case_insensitive_code_match(self):
        r = check_bst_rules({"BST": None}, [" BST ", "loxo"])
        assert len(r) == 1 and r[0]["rule_id"] == "bst-value-missing"

    def test_lowercase_vitals_key(self):
        r = check_bst_rules({"bst": 200}, ["loxo"])
        assert len(r) == 1 and r[0]["rule_id"] == "bst-code-missing"


# ───────────────────────── Pediatric dose rules ─────────────────────────
class TestPediatricSkipConditions:
    def test_drug_list_none_skips(self, tysy_only_drug_list):
        r = check_pediatric_formulation_dose(
            orders=["tysy"], patient_type="소아", age_years=5,
            vitals_context={"BW": 15}, drug_list=None,
        )
        assert r == []

    def test_empty_drug_list_skips(self):
        r = check_pediatric_formulation_dose(
            orders=["tysy"], patient_type="소아", age_years=5,
            vitals_context={"BW": 15}, drug_list={"drugs": {}},
        )
        assert r == []

    def test_non_pediatric_skips(self, tysy_only_drug_list):
        r = check_pediatric_formulation_dose(
            orders=["tysy"], patient_type="성인", age_years=30,
            vitals_context={"BW": 60}, drug_list=tysy_only_drug_list,
        )
        assert r == []

    def test_age_unknown_skips(self, tysy_only_drug_list):
        # 나이 정보 전혀 없음 → skip (unknown 결과 안 냄).
        r = check_pediatric_formulation_dose(
            orders=["tysy"], vitals_context={"BW": 15},
            drug_list=tysy_only_drug_list,
        )
        assert r == []

    def test_no_target_drug_in_orders(self, tysy_only_drug_list):
        r = check_pediatric_formulation_dose(
            orders=["loxo", "cetisy"], patient_type="소아", age_years=5,
            vitals_context={"BW": 15}, drug_list=tysy_only_drug_list,
        )
        assert r == []


class TestPediatricWeightBracket:
    def test_tysy_normal_dose_passes(self, tysy_only_drug_list):
        # 15kg 아이에 5mL TID → 표에 정확히 일치.
        r = check_pediatric_formulation_dose(
            orders=["tysy"],
            order_details=[{"code": "tysy", "dose": 5, "freq": 3}],
            patient_type="소아", age_years=5,
            vitals_context={"BW": 15},
            drug_list=tysy_only_drug_list,
        )
        assert r == []

    def test_tysy_off_recommended_gives_info(self, tysy_only_drug_list):
        # 15kg 아이에 8mL TID → 권장 5mL 초과 (tolerance 15% 초과).
        r = check_pediatric_formulation_dose(
            orders=["tysy"],
            order_details=[{"code": "tysy", "dose": 8, "freq": 3}],
            patient_type="소아", age_years=5,
            vitals_context={"BW": 15},
            drug_list=tysy_only_drug_list,
        )
        assert any(x["severity"] == SEVERITY_INFO for x in r)

    def test_tysy_over_medical_max_gives_warn(self, tysy_only_drug_list):
        # 15kg, 15mL × QID = 60mL/day = 1920mg. 15×75 = 1125mg. 초과.
        r = check_pediatric_formulation_dose(
            orders=["tysy"],
            order_details=[{"code": "tysy", "dose": 15, "freq": 4}],
            patient_type="소아", age_years=5,
            vitals_context={"BW": 15},
            drug_list=tysy_only_drug_list,
        )
        assert any(x["severity"] == SEVERITY_WARN for x in r)

    def test_tysy_bw_missing_gives_unknown(self, tysy_only_drug_list):
        r = check_pediatric_formulation_dose(
            orders=["tysy"],
            order_details=[{"code": "tysy", "dose": 5, "freq": 3}],
            patient_type="소아", age_years=5,
            vitals_context={"BW": None},
            drug_list=tysy_only_drug_list,
        )
        assert any(x["severity"] == SEVERITY_UNKNOWN for x in r)

    def test_tysy_bw_uncertain_gives_unknown(self, tysy_only_drug_list):
        r = check_pediatric_formulation_dose(
            orders=["tysy"],
            order_details=[{"code": "tysy", "dose": 5, "freq": 3}],
            patient_type="소아", age_years=5,
            vitals_context={"BW": "?"},
            drug_list=tysy_only_drug_list,
        )
        assert any(x["severity"] == SEVERITY_UNKNOWN for x in r)

    def test_tysy_ocr_noisy_bw(self, tysy_only_drug_list):
        # OCR "15kg" → 15.0 으로 파싱 후 정상.
        r = check_pediatric_formulation_dose(
            orders=["tysy"],
            order_details=[{"code": "tysy", "dose": 5, "freq": 3}],
            patient_type="소아", age_years=5,
            vitals_context={"BW": "15kg"},
            drug_list=tysy_only_drug_list,
        )
        assert r == []

    def test_tysy_bw_out_of_bracket(self, tysy_only_drug_list):
        # 6kg 아이 (최소 구간 12kg 미만). 테이블 밖 → info.
        r = check_pediatric_formulation_dose(
            orders=["tysy"],
            order_details=[{"code": "tysy", "dose": 2, "freq": 3}],
            patient_type="소아", age_years=1,
            vitals_context={"BW": 6},
            drug_list=tysy_only_drug_list,
        )
        assert any("구간 테이블 범위 밖" in x["message"] for x in r)


class TestPediatricAgeBracket:
    def test_umk_normal(self, umk_only_drug_list):
        r = check_pediatric_formulation_dose(
            orders=["umk"],
            order_details=[{"code": "umk", "dose": 6, "freq": 3}],
            age_minor="6~9세", patient_type="소아",
            drug_list=umk_only_drug_list,
        )
        assert r == []

    def test_umk_wrong_dose_strict_warn(self, umk_only_drug_list):
        # tolerance=0 → 벗어나면 warn (info 아님).
        r = check_pediatric_formulation_dose(
            orders=["umk"],
            order_details=[{"code": "umk", "dose": 12, "freq": 3}],
            age_minor="6~9세", patient_type="소아",
            drug_list=umk_only_drug_list,
        )
        assert any(x["severity"] == SEVERITY_WARN for x in r)

    def test_umk_age_minor_missing_unknown(self, umk_only_drug_list):
        # age_minor 없이 age_years 만 → age_bracket rule 은 age_minor 필수.
        r = check_pediatric_formulation_dose(
            orders=["umk"],
            order_details=[{"code": "umk", "dose": 6, "freq": 3}],
            age_years=7, patient_type="소아",
            drug_list=umk_only_drug_list,
        )
        assert any(x["severity"] == SEVERITY_UNKNOWN for x in r)

    def test_umk_age_out_of_table(self, umk_only_drug_list):
        # umk 테이블에 정의되지 않은 age_minor → info.
        r = check_pediatric_formulation_dose(
            orders=["umk"],
            order_details=[{"code": "umk", "dose": 6, "freq": 3}],
            age_minor="10~12세", patient_type="소아",
            drug_list=umk_only_drug_list,
        )
        assert any(x["severity"] == SEVERITY_INFO for x in r)


class TestPediatricHospitalDailyCap:
    def test_augsy_under_hospital_cap_under_medical_max(self, augsy_only_drug_list):
        # 30kg 아이, 10mL TID = 30mL/day = 1200mg = 40 mg/kg/day. 모두 안전.
        r = check_pediatric_formulation_dose(
            orders=["augsy"],
            order_details=[{"code": "augsy", "dose": 10, "freq": 3}],
            age_minor="6~9세", patient_type="소아", age_years=9,
            vitals_context={"BW": 30},
            drug_list=augsy_only_drug_list,
        )
        assert r == []

    def test_augsy_over_hospital_cap_only(self, augsy_only_drug_list):
        # 30kg 아이, 15mL TID = 45mL/day = 1800mg = 60 mg/kg/day. 원내 초과, 의학적 안전.
        r = check_pediatric_formulation_dose(
            orders=["augsy"],
            order_details=[{"code": "augsy", "dose": 15, "freq": 3}],
            age_minor="6~9세", patient_type="소아", age_years=9,
            vitals_context={"BW": 30},
            drug_list=augsy_only_drug_list,
        )
        severities = [x["severity"] for x in r]
        assert SEVERITY_INFO in severities
        assert SEVERITY_WARN not in severities

    def test_augsy_over_medical_max(self, augsy_only_drug_list):
        # 15kg 아이, 15mL TID = 45mL/day = 1800mg = 120 mg/kg/day. 의학적 초과.
        r = check_pediatric_formulation_dose(
            orders=["augsy"],
            order_details=[{"code": "augsy", "dose": 15, "freq": 3}],
            age_minor="2~6세", patient_type="소아", age_years=5,
            vitals_context={"BW": 15},
            drug_list=augsy_only_drug_list,
        )
        severities = [x["severity"] for x in r]
        assert SEVERITY_INFO in severities
        assert SEVERITY_WARN in severities

    def test_augsy_bw_missing_dose_present(self, augsy_only_drug_list):
        # GPT redline #3 (2026-04-24): BW missing + medical_max 정의된 약
        # → 원내 상한 초과는 info, 의학적 max 는 unknown 으로 명시 (조용한 skip 금지).
        # 45mL/day > 30mL 이므로 info. BW 없어 warn 못 내지만 unknown 필수.
        r = check_pediatric_formulation_dose(
            orders=["augsy"],
            order_details=[{"code": "augsy", "dose": 15, "freq": 3}],
            age_minor="2~6세", patient_type="소아", age_years=5,
            vitals_context={"BW": None},
            drug_list=augsy_only_drug_list,
        )
        severities = [x["severity"] for x in r]
        assert SEVERITY_INFO in severities, f"원내 info 없음: {severities}"
        assert SEVERITY_UNKNOWN in severities, f"의학적 max unknown 없음: {severities}"
        assert SEVERITY_WARN not in severities, f"BW 없는데 warn 나옴: {severities}"

    def test_augsy_dose_missing(self, augsy_only_drug_list):
        # GPT redline #2 (2026-04-24): dose 파싱 실패 시 silent skip 아니라 unknown.
        r = check_pediatric_formulation_dose(
            orders=["augsy"],
            order_details=[{"code": "augsy"}],   # dose / freq 없음
            age_minor="2~6세", patient_type="소아", age_years=5,
            vitals_context={"BW": 15},
            drug_list=augsy_only_drug_list,
        )
        assert any(x["severity"] == SEVERITY_UNKNOWN for x in r), \
            f"dose 없음에 unknown 결과 안 나옴: {r}"


class TestPediatricNeedsReview:
    def test_needs_review_drug_info_only(self):
        drug_list = {
            "drugs": {
                "suda2": {
                    "name": "코비안에스시럽",
                    "dosing_rule_type": "needs_review",
                    "raw_docx_note": "Kg보다 약간 아래 3의 배수",
                    "needs_review": True,
                },
            }
        }
        r = check_pediatric_formulation_dose(
            orders=["suda2"],
            order_details=[{"code": "suda2", "dose": 5, "freq": 3}],
            patient_type="소아", age_years=5,
            vitals_context={"BW": 15},
            drug_list=drug_list,
        )
        assert len(r) == 1
        assert r[0]["severity"] == SEVERITY_INFO
        assert "미확정" in r[0]["message"]


class TestPediatricRealJsonLoad:
    """실제 rules/pediatric_drug_list.json 을 로드하는 통합 smoke test."""

    def test_json_loads(self):
        drug_list = load_pediatric_drug_list()
        # repo root 에서 실행하지 않으면 None 반환 가능. 그땐 skip.
        if drug_list is None:
            pytest.skip("rules/pediatric_drug_list.json 없음 (repo root 에서 실행 필요).")
        assert "drugs" in drug_list
        assert len(drug_list["drugs"]) >= 6   # 최소 seed 약 수

    def test_real_tysy_normal_case(self):
        drug_list = load_pediatric_drug_list()
        if drug_list is None:
            pytest.skip("curated list 로드 실패.")
        r = check_pediatric_formulation_dose(
            orders=["tysy"],
            order_details=[{"code": "tysy", "dose": 5, "freq": 3}],
            age_minor="2~6세", patient_type="소아", age_years=5,
            vitals_context={"BW": 15},
            drug_list=drug_list,
        )
        assert r == []   # 정상 용량, 알림 없어야 함
