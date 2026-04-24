"""Migrate rules/rules.json v0.3 to v1 for session 5.

Outputs:
  - rules/rules.json: v1 safety + clinical_policy rules only
  - rules/archive/rules_v03_dropped.json: dropped legacy rules with review metadata

Run from repo root:
  python scripts/session5_migrate_rules_v3.py --dry-run
  python scripts/session5_migrate_rules_v3.py
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = REPO_ROOT / "rules" / "rules.json"
ARCHIVE_PATH = REPO_ROOT / "rules" / "archive" / "rules_v03_dropped.json"
BACKUP_PATH = REPO_ROOT / "rules" / "rules.json.bak"

MIGRATION_DATE = "2026-04-25"
SESSION_ID = 5

MIGRATE_RULES: Dict[str, Dict[str, Any]] = {
    "ped_iv_ban": {
        "rule_id": "ped-iv-ban",
        "purpose": "clinical_policy",
        "severity": "warn",
        "trigger": "patient-context+order",
        "fallback_if_uncertain": "unknown",
        "message": "만 12세 미만 소아 IV 수액은 원내 원칙상 제한",
        "sub": (
            "의학적 절대 금기가 아니라 24시열린의원 원내 운영 규칙. "
            "tamiiv(페라미플루 IV)도 IV 수액이므로 동일하게 제한 대상. "
            "예외적 필요 시 진료의가 혈관 상태, 협조도, 임상 필요성을 확인 후 결정."
        ),
        "source": "rules.json v0.3 ped_iv_ban + 2026-04-25 붕쌤 정정",
    },
    "tamiiv_info": {
        "rule_id": "tamiiv-single-dose",
        "purpose": "safety",
        "severity": "info",
        "trigger": "order-only",
        "fallback_if_uncertain": "unknown",
        "message": "tamiiv: 1회 투여로 완료",
        "sub": "5일 연속 투여 아님.",
        "source": "rules.json v0.3 tamiiv_info",
    },
    "dige_banned": {
        "rule_id": "dige-market-withdrawn",
        "purpose": "safety",
        "severity": "warn",
        "trigger": "order-only",
        "fallback_if_uncertain": "unknown",
        "message": "dige 처방 불가 — ranitidine 국내 시장 철수",
        "sub": "대체: reba(무코란) 또는 ppiiv(판타졸주사). 시장 재승인 시 rule unpublish.",
        "source": "rules.json v0.3 dige_banned (2020년 NDMA 이슈 이후 철수)",
    },
}

DROP_META: Dict[str, Dict[str, Any]] = {
    "adult_antitussive_over2": {"drop_category": "claim_automation", "drop_reason": "'2종까지만 보험' = 삭감 기준. 임상 안전 이슈 아님."},
    "adult_sputum_dup": {"drop_category": "claim_automation", "drop_reason": "'f12 비급여 처리' = 청구 해결법."},
    "ped_antitussive_over": {"drop_category": "batch2_redesign", "drop_reason": "보험 기준. 소아 polypharmacy 경고는 Batch 2에서 별도 safety rule로 재설계 가능.", "batch2_candidate": True, "note": "소아 다제병용 safety rule로 재설계 검토."},
    "ac_erdo_required_dx": {"drop_category": "claim_automation", "drop_reason": "상병 누락 경고. 차트 수정으로 해결."},
    "umk_required_dx": {"drop_category": "claim_automation", "drop_reason": "상병 누락 경고. 차트 수정으로 해결."},
    "umk_dose": {"drop_category": "superseded_by_new_rule", "drop_reason": "Rule-Pediatric-Formulation-Dose가 umk를 대체. 1세 미만은 별도 급여 이슈.", "payer_notice_candidate": True, "note": "1세 미만 umk는 의학적 금기가 아니라 급여/허가 용법용량 인정 범위 이슈."},
    "tan_lower_resp": {"drop_category": "claim_automation", "drop_reason": "'1달 100ml 보험' = 청구 제한."},
    "atock_pat_dx": {"drop_category": "claim_automation", "drop_reason": "상병 누락 경고."},
    "loxo_resp": {"drop_category": "claim_automation", "drop_reason": "'근골격계 상병 추가 필요' = 삭감 회피."},
    "inj_2types": {"drop_category": "claim_automation", "drop_reason": "'-b 비급여 코드' = 청구."},
    "dexa_required_dx": {"drop_category": "claim_automation", "drop_reason": "상병 누락 경고."},
    "genta_resp_ban": {"drop_category": "claim_automation", "drop_reason": "v1 scope에서는 청구/적응증 단독 경고 제외. 원내 실수 케이스 드물다는 판단.", "batch2_candidate": True, "latent_safety_candidate": True, "revisit_condition": "gentamicin respiratory-only 처방 또는 near-miss 발생 시 safety rule 승격 검토."},
    "tamiflu_dx": {"drop_category": "claim_automation", "drop_reason": "상병 누락 경고."},
    "tamiflu_prophylaxis": {"drop_category": "claim_automation", "drop_reason": "'f12 비보험, 특정내역 삭제' = 청구."},
    "glia8_age": {"drop_category": "payer_rule", "drop_reason": "60세 미만 본인부담 80% 선별급여. 의학적 금기 아님.", "payer_notice_candidate": True, "note": "향후 payer_notice plane 구현 시 적용 후보."},
    "cd_order": {"drop_category": "claim_automation", "drop_reason": "상병 순서 = 청구."},
    "z_code_primary": {"drop_category": "claim_automation", "drop_reason": "주상병 순서 = 청구."},
    "antibiotics_no_dx": {"drop_category": "claim_automation", "drop_reason": "상병 누락 경고."},
}

EXPECTED_IDS = set(MIGRATE_RULES) | set(DROP_META)


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def validate_legacy(legacy: Dict[str, Any]) -> None:
    if legacy.get("version") != "0.3":
        raise ValueError(f"expected rules.json version 0.3, got {legacy.get('version')!r}")
    rules = legacy.get("rules", [])
    legacy_ids = {r.get("id") for r in rules}
    missing = legacy_ids - EXPECTED_IDS
    extra = EXPECTED_IDS - legacy_ids
    if missing:
        raise ValueError(f"legacy rules without migration mapping: {sorted(missing)}")
    if extra:
        raise ValueError(f"migration mapping without legacy rule: {sorted(extra)}")
    if len(rules) != 21:
        raise ValueError(f"expected 21 legacy rules, got {len(rules)}")


def build_new_rules(legacy: Dict[str, Any]) -> Dict[str, Any]:
    migrated = [MIGRATE_RULES[r["id"]] for r in legacy["rules"] if r["id"] in MIGRATE_RULES]
    return {
        "version": "1.0",
        "schema": "v3-rule-result",
        "migrated_from": legacy.get("version", "0.3"),
        "migrated_at": MIGRATION_DATE,
        "migrated_by_session": SESSION_ID,
        "decision_doc": "rules-v03-reclassification-final",
        "scope": "v1 safety + clinical_policy rules only. 청구 rule 은 archive 참조.",
        "rules": migrated,
    }


def build_archive(legacy: Dict[str, Any]) -> Dict[str, Any]:
    dropped = []
    for rule in legacy["rules"]:
        rule_id = rule["id"]
        if rule_id not in DROP_META:
            continue
        meta = DROP_META[rule_id]
        dropped.append({
            "original": rule,
            "classification": "drop",
            "drop_category": meta["drop_category"],
            "drop_reason": meta["drop_reason"],
            "reviewed_by": "붕쌤",
            "batch2_candidate": bool(meta.get("batch2_candidate", False)),
            "latent_safety_candidate": bool(meta.get("latent_safety_candidate", False)),
            "payer_notice_candidate": bool(meta.get("payer_notice_candidate", False)),
            **({"note": meta["note"]} if "note" in meta else {}),
            **({"revisit_condition": meta["revisit_condition"]} if "revisit_condition" in meta else {}),
        })
    return {
        "schema_version": "0.3",
        "archived_at": MIGRATION_DATE,
        "archived_by_session": SESSION_ID,
        "decision_doc": "rules-v03-reclassification-final",
        "global_reason": "v1 excludes claim automation and payer-only warnings.",
        "legacy_source_meta": {k: legacy.get(k) for k in ("version", "scope", "source", "note")},
        "dropped_rules": dropped,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rules-path", default=str(RULES_PATH))
    parser.add_argument("--archive-path", default=str(ARCHIVE_PATH))
    parser.add_argument("--backup-path", default=str(BACKUP_PATH))
    args = parser.parse_args()

    rules_path = Path(args.rules_path)
    archive_path = Path(args.archive_path)
    backup_path = Path(args.backup_path)

    legacy = _load_json(rules_path)
    validate_legacy(legacy)
    new_rules = build_new_rules(legacy)
    archive = build_archive(legacy)

    print(f"[OK] validation passed: {len(legacy['rules'])} legacy rules")
    print(f"[OK] migrate: {len(new_rules['rules'])}, drop: {len(archive['dropped_rules'])}")

    if args.dry_run:
        print("[DRY] no files written")
        return 0

    shutil.copy2(rules_path, backup_path)
    _write_json(rules_path, new_rules)
    _write_json(archive_path, archive)
    print(f"[OK] backup: {backup_path}")
    print(f"[OK] wrote: {rules_path}")
    print(f"[OK] wrote: {archive_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
