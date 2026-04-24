"""
Rule-Pediatric-Formulation-Dose (v3 §8.5.1)

참조 문서:
    - design/system-overview-v3.md §8.5.1
    - decisions/decision-2026-04-21-capture-regions-and-rules.md §5

발동 조건 (AND):
    1. 12세 미만 환자 (age_minor 또는 age_years 또는 legacy patient_type="소아")
    2. 오더에 curated list 에 등록된 약 포함
    3. curated list 가 로드되고 비어있지 않음

Severity branches (v3 §8.5.1):
    - BW null/unknown        → severity=unknown (omission 아님, unknown)
    - BW 있음 + 용량 권장 벗어남   → severity=info
    - BW 있음 + 의학적 최대 초과   → severity=warn
    - 약 needs_review=true   → severity=info "체중 기반 확인 대상" (용량 비교 skip)

입력 계약:
    orders:                   list/set[str]. 정규화된 코드.
    order_details:            list[dict]. 각 {code, dose, freq, days}. None 가능.
    age_minor:                str (16구간 중). None 가능 → age_years 폴백.
    age_years:                int. None 가능.
    patient_type:             "소아"/"성인". legacy 폴백.
    vitals_context:           dict. {"BW": number_or_sentinel, ...}. None → pediatric rule 유효 이나 BW 없음 처리.
    drug_list:                load 된 JSON dict. None 가능 → rule skip.

반환:
    list[RuleResult]. 빈 리스트면 통과.

설계:
    - curated list 가 None/empty 면 전체 skip.
    - 소아가 아니면 skip.
    - 각 대상 약별로 check_drug_dose() 호출.
    - 하나의 processing 에서 같은 rule_id 로 여러 결과 나올 수 있음 (약 여러 개 + 각각 fail).
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.rules_v2.age_utils import AGE_MINOR_UNDER_12, is_age_minor_under_12
from app.rules_v2.schema import (
    PURPOSE_SAFETY,
    SEVERITY_INFO,
    SEVERITY_UNKNOWN,
    SEVERITY_WARN,
    make_result,
)
from app.rules_v2.vitals_utils import (
    VITAL_STATE_PRESENT,
    VITAL_STATE_UNAVAILABLE,
    coerce_float,
    vital_state,
)


logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────────────────────
RULE_ID = "pediatric-formulation-dose"
_TRIGGER = "patient-context+vitals+order"
_SOURCE = "v3 §8.5.1 / decisions/decision-2026-04-21-capture-regions-and-rules.md"


# ─────────────────────────────────────────────────────────────
# Curated list 로더
# ─────────────────────────────────────────────────────────────
def load_pediatric_drug_list(
    path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """
    rules/pediatric_drug_list.json 을 로드.

    반환:
        dict — 로드 성공. "drugs" 키에 약 정보.
        None — 파일 없음/파싱 실패. 호출측은 rule 전체 skip 해야 함.

    fail-silent 이유:
        - 배포 환경에 아직 JSON 이 없을 수 있음 (신규 기능).
        - JSON 파싱 실패 시 crash 대신 log + skip. 운영 모니터링으로 감지.
    """
    if path is None:
        # 프로젝트 루트 기준 기본 경로.
        path = Path("rules") / "pediatric_drug_list.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.warning(
            "[pediatric_dose] curated list file not found: %s. Rule will be skipped.",
            path,
        )
        return None
    except json.JSONDecodeError as e:
        logger.error(
            "[pediatric_dose] curated list JSON parse failed: %s. Rule will be skipped. error=%s",
            path, e,
        )
        return None

    if not isinstance(data, dict) or "drugs" not in data:
        logger.error(
            "[pediatric_dose] curated list malformed (no 'drugs' key): %s. Skipping.",
            path,
        )
        return None

    return data


def _active_drugs(drug_list: Dict[str, Any]) -> Dict[str, dict]:
    """
    drug_list['drugs'] 에서 '_comment' 같은 placeholder 키 제외하고 실제 약만.
    """
    drugs = drug_list.get("drugs") or {}
    return {
        code: spec
        for code, spec in drugs.items()
        if not code.startswith("_") and isinstance(spec, dict)
    }


# ─────────────────────────────────────────────────────────────
# 내부 헬퍼
# ─────────────────────────────────────────────────────────────
def _first_order_detail(
    order_details: Optional[List[Dict[str, Any]]],
    code: str,
) -> Optional[Dict[str, Any]]:
    """order_details 리스트에서 code 와 일치하는 첫 번째 항목."""
    if not order_details:
        return None
    for item in order_details:
        if not isinstance(item, dict):
            continue
        item_code = str(item.get("code", "")).strip().lower()
        if item_code == code.lower():
            return item
    return None


def _find_weight_bracket(
    brackets: List[Dict[str, Any]],
    bw: float,
) -> Optional[Dict[str, Any]]:
    """체중 구간 테이블에서 bw 에 해당하는 구간 찾기."""
    for b in brackets:
        kg_min = b.get("weight_kg_min")
        kg_max = b.get("weight_kg_max")   # None 이면 상한 없음
        if kg_min is None:
            continue
        if bw < float(kg_min):
            continue
        if kg_max is not None and bw > float(kg_max):
            continue
        return b
    return None


def _is_under_12(
    age_minor: Optional[str],
    age_years: Optional[int],
    patient_type: Optional[str],
) -> Optional[bool]:
    """
    age_utils 판정 + legacy patient_type 폴백.

    반환:
        True  → 12세 미만.
        False → 12세 이상.
        None  → 완전 정보 부족 (rule 은 skip 하지 않고, 호출측이 unknown 으로).
    """
    verdict = is_age_minor_under_12(age_minor=age_minor, age_years=age_years)
    if verdict is not None:
        return verdict
    # legacy 폴백: 기존 parser 는 patient_type="소아" 를 "12세 미만" 으로 사용 중.
    if patient_type == "소아":
        return True
    if patient_type == "성인":
        return False
    return None


# ─────────────────────────────────────────────────────────────
# 약별 용량 체크 (dosing_rule_type 분기)
# ─────────────────────────────────────────────────────────────
def _exceeds_tolerance(actual: float, expected: float, tolerance_pct: float) -> bool:
    """actual 이 expected ± tolerance_pct 범위 밖이면 True."""
    if expected <= 0:
        return False
    tol = expected * (tolerance_pct / 100.0)
    return actual < expected - tol or actual > expected + tol


def _check_medical_max(
    code: str,
    spec: Dict[str, Any],
    bw: float,
    daily_ml: Optional[float],
) -> Optional[Dict[str, Any]]:
    """
    의학적 절대 금기 (mg/kg/day) 초과 검사.
    초과하면 warn RuleResult 반환, 아니면 None.
    """
    max_mg_per_kg_day = spec.get("medical_max_mg_per_kg_per_day")
    conc = spec.get("concentration_mg_per_ml")
    if max_mg_per_kg_day is None or conc is None or daily_ml is None:
        return None
    daily_mg = daily_ml * float(conc)
    max_daily_mg = float(max_mg_per_kg_day) * bw
    if daily_mg > max_daily_mg:
        return make_result(
            rule_id=RULE_ID,
            purpose=PURPOSE_SAFETY,
            severity=SEVERITY_WARN,
            trigger=_TRIGGER,
            message=f"{spec.get('name', code)} 의학적 최대 용량 초과",
            sub=(
                f"현재 약 {daily_mg:.0f} mg/day ({daily_mg/bw:.1f} mg/kg/day). "
                f"의학적 상한: {max_mg_per_kg_day} mg/kg/day × {bw:g}kg = {max_daily_mg:.0f} mg/day. "
                f"{spec.get('medical_max_note', '')}"
            ).strip(),
            source=_SOURCE,
            fallback_if_uncertain=SEVERITY_UNKNOWN,
            extra={
                "matched_code": code,
                "bw": bw,
                "daily_mg": daily_mg,
                "max_daily_mg": max_daily_mg,
            },
        )
    return None


def _check_weight_bracket_fixed(
    code: str,
    spec: Dict[str, Any],
    bw: float,
    dose: Optional[float],
    freq: Optional[float],
) -> List[Dict[str, Any]]:
    """
    체중 구간별 1회 용량 고정 약 (tysy, dexisy, cetisy, keto2, di, d).
    """
    results: List[Dict[str, Any]] = []
    brackets = spec.get("weight_brackets") or []
    bracket = _find_weight_bracket(brackets, bw)

    name = spec.get("name") or code
    unit = spec.get("unit") or "mL"
    freq_typical = spec.get("typical_freq_per_day")
    tolerance = spec.get("tolerance_pct", 15)

    if bracket is None:
        # 체중 구간 table 범위 밖. 예: 6kg 미만 tysy 등.
        results.append(make_result(
            rule_id=RULE_ID,
            purpose=PURPOSE_SAFETY,
            severity=SEVERITY_INFO,
            trigger=_TRIGGER,
            message=f"{name} 체중 구간 테이블 범위 밖 (BW={bw:g}kg)",
            sub="원내 체중 구간 테이블에 해당 체중 범위 없음. 수기 용량 확인 필요.",
            source=_SOURCE,
            fallback_if_uncertain=SEVERITY_UNKNOWN,
            extra={"matched_code": code, "bw": bw},
        ))
        return results

    expected_per_dose = bracket.get("per_dose_ml")
    if expected_per_dose is None:
        return results  # 스펙 불완전
    expected_per_dose = float(expected_per_dose)

    if dose is None:
        results.append(make_result(
            rule_id=RULE_ID,
            purpose=PURPOSE_SAFETY,
            severity=SEVERITY_UNKNOWN,
            trigger=_TRIGGER,
            message=f"{name} 1회 용량 파싱 실패",
            sub=(
                f"BW={bw:g}kg 기준 권장 1회량: {expected_per_dose:g}{unit}. "
                "order_details.dose 가 비어있어 비교 보류."
            ),
            source=_SOURCE,
            fallback_if_uncertain=SEVERITY_UNKNOWN,
            extra={"matched_code": code, "bw": bw},
        ))
        return results

    # 1회 용량 비교
    if _exceeds_tolerance(dose, expected_per_dose, tolerance):
        results.append(make_result(
            rule_id=RULE_ID,
            purpose=PURPOSE_SAFETY,
            severity=SEVERITY_INFO,
            trigger=_TRIGGER,
            message=f"{name} 1회 용량이 원내 권장과 다름",
            sub=(
                f"현재 1회 {dose:g}{unit}, 권장 {expected_per_dose:g}{unit} (±{tolerance}%). "
                f"BW={bw:g}kg 구간. 최종 판단은 진료의."
            ),
            source=_SOURCE,
            fallback_if_uncertain=SEVERITY_UNKNOWN,
            extra={
                "matched_code": code, "bw": bw,
                "dose_given": dose, "dose_expected": expected_per_dose,
            },
        ))

    # 1일 총량 + 의학적 최대 검사
    daily = dose * freq if (freq is not None and freq > 0) else None
    if daily is None and freq_typical:
        daily = dose * float(freq_typical)

    med_result = _check_medical_max(code, spec, bw, daily)
    if med_result is not None:
        results.append(med_result)

    return results


def _check_age_bracket_fixed(
    code: str,
    spec: Dict[str, Any],
    age_minor: Optional[str],
    dose: Optional[float],
    freq: Optional[float],
) -> List[Dict[str, Any]]:
    """
    나이 구간별 1일 총량 고정 (umk).
    """
    results: List[Dict[str, Any]] = []
    age_brackets = spec.get("age_brackets") or {}
    name = spec.get("name") or code
    unit = spec.get("unit") or "mL"

    if not age_minor:
        results.append(make_result(
            rule_id=RULE_ID,
            purpose=PURPOSE_SAFETY,
            severity=SEVERITY_UNKNOWN,
            trigger=_TRIGGER,
            message=f"{name} 나이 구간 판정 불가",
            sub="age_minor 값이 없어 나이 기반 용량 비교 보류. parser 가 age_minor 채워야 정상.",
            source=_SOURCE,
            fallback_if_uncertain=SEVERITY_UNKNOWN,
            extra={"matched_code": code},
        ))
        return results

    entry = age_brackets.get(age_minor)
    if entry is None:
        # 이 약의 나이 테이블 밖. 예: 10~12세 umk 는 OK 인데 12~15세는 밖.
        results.append(make_result(
            rule_id=RULE_ID,
            purpose=PURPOSE_SAFETY,
            severity=SEVERITY_INFO,
            trigger=_TRIGGER,
            message=f"{name} 나이 구간 테이블 범위 밖 ({age_minor})",
            sub="해당 나이 구간에 대한 고정 용량 정의 없음.",
            source=_SOURCE,
            fallback_if_uncertain=SEVERITY_UNKNOWN,
            extra={"matched_code": code, "age_minor": age_minor},
        ))
        return results

    expected_daily = entry.get("daily_total_ml")
    expected_per_dose = entry.get("per_dose_ml")

    if dose is None:
        results.append(make_result(
            rule_id=RULE_ID,
            purpose=PURPOSE_SAFETY,
            severity=SEVERITY_UNKNOWN,
            trigger=_TRIGGER,
            message=f"{name} 1회 용량 파싱 실패",
            sub=(
                f"age_minor={age_minor} 기준 권장 1일 {expected_daily}{unit}, "
                f"1회 {expected_per_dose}{unit}. order_details.dose 비어있음."
            ),
            source=_SOURCE,
            fallback_if_uncertain=SEVERITY_UNKNOWN,
            extra={"matched_code": code},
        ))
        return results

    tolerance = float(spec.get("tolerance_pct", 0))
    # 1회 용량 비교
    if expected_per_dose is not None and _exceeds_tolerance(
        dose, float(expected_per_dose), tolerance
    ):
        results.append(make_result(
            rule_id=RULE_ID,
            purpose=PURPOSE_SAFETY,
            severity=SEVERITY_WARN if tolerance == 0 else SEVERITY_INFO,
            trigger=_TRIGGER,
            message=f"{name} 용량이 나이 기반 고정 용량과 다름",
            sub=(
                f"age_minor={age_minor}. 권장 1회 {expected_per_dose}{unit}, 1일 {expected_daily}{unit}. "
                f"현재 1회 {dose:g}{unit}. {spec.get('note', '')}"
            ).strip(),
            source=_SOURCE,
            fallback_if_uncertain=SEVERITY_UNKNOWN,
            extra={
                "matched_code": code, "age_minor": age_minor,
                "dose_given": dose, "dose_expected": expected_per_dose,
            },
        ))

    return results


def _check_hospital_daily_cap_only(
    code: str,
    spec: Dict[str, Any],
    bw: Optional[float],
    bw_state: str,
    dose: Optional[float],
    freq: Optional[float],
) -> List[Dict[str, Any]]:
    """
    augsy 같이 원내 '하루 30mL 상한' 만 있는 약.
    BW 기반 의학적 최대는 medical_max_mg_per_kg_per_day 로 별도 검사.

    bw 는 vital_state 가 PRESENT 일 때만 float, 그 외 None.
    bw_state 는 v3 §7.5 "조용한 skip 금지" 원칙을 지키기 위해 따로 전달받음.
    """
    results: List[Dict[str, Any]] = []
    name = spec.get("name") or code
    unit = spec.get("unit") or "mL"
    freq_typical = spec.get("typical_freq_per_day")
    cap = spec.get("hospital_recommended_daily_max_ml")
    has_medical_max = spec.get("medical_max_mg_per_kg_per_day") is not None

    # dose 파싱 실패 (GPT redline #2, 2026-04-24):
    # v3 §7.5 조용한 skip 금지 원칙 → 평가 불가 명시.
    if dose is None:
        return [make_result(
            rule_id=RULE_ID,
            purpose=PURPOSE_SAFETY,
            severity=SEVERITY_UNKNOWN,
            trigger=_TRIGGER,
            message=f"{name} 1회 용량 파싱 실패 — 용량 판정 보류",
            sub=(
                "hospital_daily_cap_only 약제이므로 order_details.dose/freq 가 필요. "
                "원내 1일 상한과 의학적 최대 모두 비교 불가."
            ),
            source=_SOURCE,
            fallback_if_uncertain=SEVERITY_UNKNOWN,
            extra={"matched_code": code},
        )]

    daily = dose * freq if (freq is not None and freq > 0) else None
    if daily is None and freq_typical:
        daily = dose * float(freq_typical)

    # 원내 상한 초과 → info
    if cap is not None and daily is not None and daily > float(cap):
        results.append(make_result(
            rule_id=RULE_ID,
            purpose=PURPOSE_SAFETY,
            severity=SEVERITY_INFO,
            trigger=_TRIGGER,
            message=f"{name} 원내 권장 1일 상한 초과",
            sub=(
                f"현재 {daily:g}{unit}/day, 원내 권장 ≤ {cap}{unit}/day. "
                f"{spec.get('alternative_if_over_hospital_cap', '')} 고려. "
                f"{spec.get('hospital_cap_note', '')}"
            ).strip(),
            source=_SOURCE,
            fallback_if_uncertain=SEVERITY_UNKNOWN,
            extra={
                "matched_code": code, "daily_ml": daily, "hospital_cap": cap,
            },
        ))

    # 의학적 절대 금기 검사 분기 (GPT redline #3, 2026-04-24):
    #   - BW PRESENT → 직접 검사
    #   - BW MISSING / UNKNOWN + medical_max 정의된 약 → unknown 결과 추가.
    #     이유: 농도 40 mg/mL augsy 에서 BW=12kg 이면 30 mL/day 도 이미 100 mg/kg/day 라
    #           의학적 금기 초과 여부를 단정할 수 없음. 조용히 pass 하면 위험.
    if bw is not None:
        med_result = _check_medical_max(code, spec, bw, daily)
        if med_result is not None:
            results.append(med_result)
    elif has_medical_max:
        results.append(make_result(
            rule_id=RULE_ID,
            purpose=PURPOSE_SAFETY,
            severity=SEVERITY_UNKNOWN,
            trigger=_TRIGGER,
            message=f"{name} 의학적 최대 용량 판정 보류 (체중 미상)",
            sub=(
                f"BW 상태={bw_state}. 농도 × daily 계산은 가능하나 "
                f"mg/kg/day 금기 판정은 체중 없이 불가."
            ),
            source=_SOURCE,
            fallback_if_uncertain=SEVERITY_UNKNOWN,
            extra={"matched_code": code, "bw_state": bw_state},
        ))

    return results


def _check_needs_review(
    code: str,
    spec: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    needs_review=true 약. 용량 비교 skip, "체중 기반 확인 대상" info 만.
    """
    name = spec.get("name") or code
    hint = spec.get("raw_docx_note") or spec.get("interpretation_draft") or ""
    return [make_result(
        rule_id=RULE_ID,
        purpose=PURPOSE_SAFETY,
        severity=SEVERITY_INFO,
        trigger=_TRIGGER,
        message=f"{name} 체중 기반 확인 대상 (용량 규칙 미확정)",
        sub=(f"원내 용량 해석 확인 필요. 메모: {hint}" if hint else "원내 용량 규칙 미확정."),
        source=_SOURCE,
        fallback_if_uncertain=SEVERITY_UNKNOWN,
        extra={"matched_code": code, "needs_review": True},
    )]


# ─────────────────────────────────────────────────────────────
# Public: Rule 평가 진입점
# ─────────────────────────────────────────────────────────────
def check_pediatric_formulation_dose(
    orders: Optional[Iterable[str]],
    order_details: Optional[List[Dict[str, Any]]] = None,
    age_minor: Optional[str] = None,
    age_years: Optional[int] = None,
    patient_type: Optional[str] = None,
    vitals_context: Optional[dict] = None,
    drug_list: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Rule-Pediatric-Formulation-Dose 평가. 0~N RuleResult 반환.

    동작:
        0. drug_list None/empty → skip (빈 리스트).
        1. 12세 미만 아니면 skip.
        2. orders ∩ curated drug codes → 대상 약 목록.
        3. 각 약별로 dosing_rule_type 분기 처리.

    skip 정책:
        - curated list 비어있음 → skip (fail-silent-skip, D3 §5 원칙).
        - 소아 판정 불가 (age 정보 전혀 없음) → skip. BST rule 과 달리 unknown 결과 안 냄.
          이유: "나이 모르는 상태에서 BW 용량 경고" 는 오탐률 매우 높음.
    """
    if drug_list is None:
        return []

    active_drugs = _active_drugs(drug_list)
    if not active_drugs:
        return []

    # 소아 판정
    under_12 = _is_under_12(age_minor=age_minor, age_years=age_years,
                             patient_type=patient_type)
    if under_12 is not True:   # False 또는 None
        return []

    # orders 정규화
    if orders is None:
        return []
    order_codes = {
        str(c).strip().lower() for c in orders if isinstance(c, str)
    }

    targets = sorted(order_codes & set(active_drugs.keys()))
    if not targets:
        return []

    # BW 상태 공용 조회
    bw_state, bw_value = vital_state(vitals_context, "BW", "bw", "body_weight")

    all_results: List[Dict[str, Any]] = []

    for code in targets:
        spec = active_drugs[code]

        # needs_review → info only
        if spec.get("needs_review"):
            all_results.extend(_check_needs_review(code, spec))
            continue

        dosing_type = spec.get("dosing_rule_type")

        # age_bracket_fixed (umk) 는 BW 안 씀. age_minor 로 판정.
        if dosing_type == "age_bracket_fixed":
            detail = _first_order_detail(order_details, code)
            dose = coerce_float(detail.get("dose")) if detail else None
            freq = coerce_float(detail.get("freq")) if detail else None
            all_results.extend(_check_age_bracket_fixed(
                code, spec, age_minor, dose, freq,
            ))
            continue

        # hospital_daily_cap_only (augsy)
        if dosing_type == "hospital_daily_cap_only":
            detail = _first_order_detail(order_details, code)
            dose = coerce_float(detail.get("dose")) if detail else None
            freq = coerce_float(detail.get("freq")) if detail else None
            # BW 는 의학적 금기 검사에만 쓰므로 없어도 원내 상한 검사는 가능.
            bw_for_aug = bw_value if bw_state == VITAL_STATE_PRESENT else None
            all_results.extend(_check_hospital_daily_cap_only(
                code, spec, bw_for_aug, bw_state, dose, freq,
            ))
            continue

        # weight_bracket_fixed (tysy, dexisy, cetisy, keto2, di, d)
        if dosing_type == "weight_bracket_fixed":
            if bw_state != VITAL_STATE_PRESENT:
                all_results.append(make_result(
                    rule_id=RULE_ID,
                    purpose=PURPOSE_SAFETY,
                    severity=SEVERITY_UNKNOWN,
                    trigger=_TRIGGER,
                    message=f"{spec.get('name', code)} 체중 없음/불확실 — 용량 판정 보류",
                    sub=f"BW 상태={bw_state}. 체중 기반 약이므로 vitals_context.BW 필요.",
                    source=_SOURCE,
                    fallback_if_uncertain=SEVERITY_UNKNOWN,
                    extra={"matched_code": code, "bw_state": bw_state},
                ))
                continue
            detail = _first_order_detail(order_details, code)
            dose = coerce_float(detail.get("dose")) if detail else None
            freq = coerce_float(detail.get("freq")) if detail else None
            all_results.extend(_check_weight_bracket_fixed(
                code, spec, bw_value, dose, freq,
            ))
            continue

        # per_kg_per_dose 등 아직 구현 안 된 dosing_rule_type
        all_results.append(make_result(
            rule_id=RULE_ID,
            purpose=PURPOSE_SAFETY,
            severity=SEVERITY_INFO,
            trigger=_TRIGGER,
            message=f"{spec.get('name', code)} 체중 기반 확인 대상 (엔진 미구현 dosing type)",
            sub=f"dosing_rule_type={dosing_type!r} 아직 v1 엔진 미구현. 수기 확인.",
            source=_SOURCE,
            fallback_if_uncertain=SEVERITY_UNKNOWN,
            extra={"matched_code": code, "dosing_rule_type": dosing_type},
        ))

    return all_results


# ─────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import copy

    # 최소 테스트용 curated list (외부 JSON 없이 단독 검증)
    TEST_DRUG_LIST = {
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
                "hospital_cap_note": "원내 관행",
            },
            "umk": {
                "name": "움카민",
                "ingredient": "pelargonium",
                "formulation": "syrup",
                "unit": "mL",
                "typical_freq_per_day": 3,
                "dosing_rule_type": "age_bracket_fixed",
                "age_brackets": {
                    "2~6세":   {"daily_total_ml": 9,  "per_dose_ml": 3},
                    "6~9세":   {"daily_total_ml": 18, "per_dose_ml": 6},
                    "9~10세":  {"daily_total_ml": 18, "per_dose_ml": 6},
                },
                "tolerance_pct": 0,
            },
            "suda2": {
                "name": "코비안에스시럽",
                "dosing_rule_type": "needs_review",
                "raw_docx_note": "Kg보다 약간 아래 3의 배수",
                "needs_review": True,
            },
        }
    }

    # ── [0] curated list 없음 → skip ──
    r = check_pediatric_formulation_dose(
        orders=["tysy"], patient_type="소아", age_years=5,
        vitals_context={"BW": 15}, drug_list=None,
    )
    assert r == []
    print("[OK] drug_list None → skip")

    # ── 소아 아님 → skip ──
    r = check_pediatric_formulation_dose(
        orders=["tysy"], patient_type="성인", age_years=30,
        vitals_context={"BW": 60}, drug_list=TEST_DRUG_LIST,
    )
    assert r == []
    print("[OK] 성인 → skip")

    # ── tysy 정상 용량 (15kg 아이, 5mL × TID) → 통과 ──
    r = check_pediatric_formulation_dose(
        orders=["tysy"], order_details=[{"code": "tysy", "dose": 5, "freq": 3}],
        patient_type="소아", age_years=5, vitals_context={"BW": 15},
        drug_list=TEST_DRUG_LIST,
    )
    assert r == [], f"정상 tysy 에 결과 나옴: {r}"
    print("[OK] tysy 정상 용량 (5mL TID, 15kg) → 통과")

    # ── tysy 권장 벗어남 (15kg 아이, 8mL × TID) → info ──
    r = check_pediatric_formulation_dose(
        orders=["tysy"], order_details=[{"code": "tysy", "dose": 8, "freq": 3}],
        patient_type="소아", age_years=5, vitals_context={"BW": 15},
        drug_list=TEST_DRUG_LIST,
    )
    assert any(x["severity"] == "info" for x in r), f"info 없음: {r}"
    print("[OK] tysy 권장 벗어남 → info")

    # ── tysy 의학적 최대 초과 (15kg, 15mL × QID = 60mL/day) ──
    # 60 × 32 = 1920 mg/day. 15 × 75 = 1125 mg/day. 초과.
    r = check_pediatric_formulation_dose(
        orders=["tysy"], order_details=[{"code": "tysy", "dose": 15, "freq": 4}],
        patient_type="소아", age_years=5, vitals_context={"BW": 15},
        drug_list=TEST_DRUG_LIST,
    )
    assert any(x["severity"] == "warn" for x in r), f"warn 없음: {r}"
    print("[OK] tysy 의학적 최대 초과 → warn")

    # ── BW 없음 → unknown ──
    r = check_pediatric_formulation_dose(
        orders=["tysy"], order_details=[{"code": "tysy", "dose": 5, "freq": 3}],
        patient_type="소아", age_years=5, vitals_context={"BW": None},
        drug_list=TEST_DRUG_LIST,
    )
    assert any(x["severity"] == "unknown" for x in r), f"unknown 없음: {r}"
    print("[OK] BW 없음 → unknown")

    # ── BW 불명확 (uncertain) → unknown ──
    r = check_pediatric_formulation_dose(
        orders=["tysy"], order_details=[{"code": "tysy", "dose": 5, "freq": 3}],
        patient_type="소아", age_years=5, vitals_context={"BW": "?"},
        drug_list=TEST_DRUG_LIST,
    )
    assert any(x["severity"] == "unknown" for x in r)
    print("[OK] BW uncertain → unknown")

    # ── augsy 원내 상한 초과 (30kg 아이, 15mL × TID = 45mL/day > 30) → info ──
    r = check_pediatric_formulation_dose(
        orders=["augsy"], order_details=[{"code": "augsy", "dose": 15, "freq": 3}],
        patient_type="소아", age_years=9, vitals_context={"BW": 30},
        drug_list=TEST_DRUG_LIST,
    )
    assert any(x["severity"] == "info" and "원내" in x["sub"] for x in r), f"원내 info 없음: {r}"
    print("[OK] augsy 원내 상한 초과 → info")

    # ── augsy 의학적 최대 초과 (15kg, 15mL TID = 45mL/day × 40mg/mL = 1800mg/day, 15×90=1350 초과) → warn ──
    r = check_pediatric_formulation_dose(
        orders=["augsy"], order_details=[{"code": "augsy", "dose": 15, "freq": 3}],
        patient_type="소아", age_years=5, vitals_context={"BW": 15},
        drug_list=TEST_DRUG_LIST,
    )
    assert any(x["severity"] == "warn" for x in r), f"warn 없음: {r}"
    print("[OK] augsy 의학적 최대 초과 → warn")

    # ── augsy dose 파싱 실패 → unknown (GPT redline #2, 2026-04-24) ──
    r = check_pediatric_formulation_dose(
        orders=["augsy"], order_details=[{"code": "augsy"}],   # dose/freq 없음
        patient_type="소아", age_years=5, vitals_context={"BW": 15},
        drug_list=TEST_DRUG_LIST,
    )
    assert any(x["severity"] == "unknown" for x in r), f"unknown 없음: {r}"
    print("[OK] augsy dose 없음 → unknown (silent skip 아님)")

    # ── augsy BW 없음 + dose 있음 → 원내 상한 체크만, 의학적 max 는 unknown (GPT redline #3) ──
    r = check_pediatric_formulation_dose(
        orders=["augsy"], order_details=[{"code": "augsy", "dose": 15, "freq": 3}],
        patient_type="소아", age_years=5, vitals_context={"BW": None},
        drug_list=TEST_DRUG_LIST,
    )
    severities = [x["severity"] for x in r]
    assert "info" in severities      # 원내 45mL > 30 초과
    assert "unknown" in severities   # medical max 판정 보류
    assert "warn" not in severities  # BW 없으니 warn 못 냄
    print("[OK] augsy BW 없음 → info (원내) + unknown (의학적 max 보류)")

    # ── umk 정상 (8세, 18mL/day, 1회 6mL) → 통과 ──
    r = check_pediatric_formulation_dose(
        orders=["umk"], order_details=[{"code": "umk", "dose": 6, "freq": 3}],
        age_minor="6~9세", patient_type="소아",
        vitals_context={"BW": 25}, drug_list=TEST_DRUG_LIST,
    )
    assert r == [], f"umk 정상에 결과 나옴: {r}"
    print("[OK] umk 나이 기반 정상 → 통과")

    # ── umk 용량 벗어남 (8세, 1회 12mL) → warn (tolerance=0) ──
    r = check_pediatric_formulation_dose(
        orders=["umk"], order_details=[{"code": "umk", "dose": 12, "freq": 3}],
        age_minor="6~9세", patient_type="소아", drug_list=TEST_DRUG_LIST,
    )
    assert any(x["severity"] == "warn" for x in r), f"umk 용량 벗어남 warn 없음: {r}"
    print("[OK] umk 용량 벗어남 → warn (tolerance=0 고정)")

    # ── needs_review 약 (suda2) → info ──
    r = check_pediatric_formulation_dose(
        orders=["suda2"], order_details=[{"code": "suda2", "dose": 5, "freq": 3}],
        patient_type="소아", age_years=5, vitals_context={"BW": 15},
        drug_list=TEST_DRUG_LIST,
    )
    assert any(x["severity"] == "info" and "미확정" in x["message"] for x in r)
    print("[OK] needs_review → info (용량 비교 skip)")

    # ── 빈 curated list → skip ──
    empty_list = {"drugs": {}}
    r = check_pediatric_formulation_dose(
        orders=["tysy"], patient_type="소아", age_years=5,
        vitals_context={"BW": 15}, drug_list=empty_list,
    )
    assert r == []
    print("[OK] 빈 curated list → skip (fail-silent)")

    # ── 여러 약 동시 ──
    r = check_pediatric_formulation_dose(
        orders=["tysy", "augsy", "umk"],
        order_details=[
            {"code": "tysy", "dose": 5, "freq": 3},
            {"code": "augsy", "dose": 15, "freq": 3},   # 원내 상한 초과
            {"code": "umk", "dose": 6, "freq": 3},
        ],
        age_minor="6~9세", patient_type="소아",
        vitals_context={"BW": 25}, drug_list=TEST_DRUG_LIST,
    )
    assert any(x.get("matched_code") == "augsy" for x in r)
    print(f"[OK] 여러 약 동시 평가 (augsy info 발동, 총 결과 수={len(r)})")

    print("\n모든 self-test 통과.")
