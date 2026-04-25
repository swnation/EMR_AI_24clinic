"""
session5_checker_patch.py
=========================

세션5 P0 진단 후속 작업 — checker.py 의 hardcoded rule 3개를
v1 rules.json (PR #14) 결정과 일치시키는 최소 침습 patch.

배경:
    - PR #14 에서 rules.json v0.3 → v1 마이그레이션 했지만, checker.py 가 rules.json 을
      읽지 않으므로 runtime 효과 없음. (Session 5 P0 Diagnosis Report 참조)
    - 이 patch 는 코드의 동등 logic 을 v1 결정에 맞춰 수정.

수정 대상:
    1. _check_injection 의 C-4 (ped_iv_ban):
       - tamiiv/tyiv 예외 제거 (모든 IV 수액 동일 적용)
       - severity err → warn (clinical_policy)
       - 문구 일반화

    2. _check_flu 의 D-3 (tamiiv_info):
       - 문구 단순화

    3. _check_common 의 E-1 (dige_banned):
       - 문구 정리 (시장 재승인 unpublish 안내 추가)

사용법:
    $ python scripts/session5_checker_patch.py --dry-run
    $ python scripts/session5_checker_patch.py

원칙:
    - 백업 파일 자동 생성 (.bak.session5)
    - dry-run 지원
    - 패치 전 정확한 매칭 검증, 못 찾으면 abort
    - 멱등성 보장 (이미 패치된 파일에 재실행 시 no-op)

근거 문서:
    - rules_v03_reclassification_final.md (2026-04-25)
    - session5_p0_diagnosis_report.md (2026-04-25)
    - GPT 2차 답변 (2026-04-25): tamiiv, tyiv 모두 예외 아님 확정
"""
import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = REPO_ROOT / "app" / "checker.py"
BACKUP_PATH = REPO_ROOT / "app" / "checker.py.bak.session5"


# ═══════════════════════════════════════════════════════════════════
# 패치 정의 — (마커 키워드, old block, new block)
# ═══════════════════════════════════════════════════════════════════

PATCH_1_PED_IV_BAN = {
    "name": "ped_iv_ban (C-4 소아 IV 수액 제한)",
    "marker_for_idempotency": "# session5: tamiiv/tyiv 예외 제거. 모든 IV 수액 동일 적용.",
    "old": '''    # C-4. 소아 수액(IV) 금지
    if patient_type == "소아":
        # tamiiv는 소아에서도 6개월 이상 가능 (별도 주의)
        iv_no_tami = (order_set & IV_FLUID_CODES) - {"tamiiv","tyiv"}
        if iv_no_tami:
            results.append({
                "level": "err",
                "message": "소아(12세 미만) 수액 처방 불가",
                "sub": f"수액코드: {', '.join(sorted(iv_no_tami))}. 14~15세 이상부터 혈관상태에 따라 가능",
                "source": "소아 독감 influenza.md"
            })''',
    "new": '''    # C-4. 소아 IV 수액 제한 (clinical_policy)
    # session5: tamiiv/tyiv 예외 제거. 모든 IV 수액 동일 적용.
    # 의학적 절대 금기가 아니라 24시열린의원 원내 운영 규칙.
    if patient_type == "소아":
        iv_orders = order_set & IV_FLUID_CODES
        if iv_orders:
            results.append({
                "level": "warn",
                "message": "만 12세 미만 소아 IV 수액은 원내 원칙상 제한",
                "sub": (
                    f"수액코드: {', '.join(sorted(iv_orders))}. "
                    "의학적 절대 금기가 아니라 24시열린의원 원내 운영 규칙. "
                    "tamiiv, tyiv 포함 모든 IV 수액이 동일하게 제한 대상. "
                    "예외적 필요 시 진료의가 혈관 상태, 협조도, 임상 필요성을 확인 후 결정."
                ),
                "source": "rules.json v0.3 ped_iv_ban + 2026-04-25 붕쌤 정정"
            })''',
}

PATCH_2_TAMIIV_INFO = {
    "name": "tamiiv_info (D-3 페라미플루 1회 투여 안내)",
    "marker_for_idempotency": "# session5: 문구 단순화. 체중 기반 용량 검증은 Batch 2 이후로 분리.",
    "old": '''        # D-3. tamiiv(페라미플루) 주의사항
        if "tamiiv" in order_set:
            results.append({
                "level": "info",
                "message": "tamiiv(페라미플루): 1회로 끝남, 5일 연속 아님",
                "sub": "성인 기본 2앰플. 6개월↑ 사용 가능. Kg당 10mL, 1앰플=150mL, 최대 300mL",
                "source": "독감 influenza.md"
            })''',
    "new": '''        # D-3. tamiiv(페라미플루) 단일 투여 안내 (safety/info)
        # session5: 문구 단순화. 체중 기반 용량 검증은 Batch 2 이후로 분리.
        if "tamiiv" in order_set:
            results.append({
                "level": "info",
                "message": "tamiiv: 1회 투여로 완료",
                "sub": "5일 연속 투여 아님.",
                "source": "rules.json v0.3 tamiiv_info"
            })''',
}

PATCH_3_DIGE_BANNED = {
    "name": "dige_banned (E-1 dige 시장 철수 안내)",
    "marker_for_idempotency": "# session5: 문구 정리. 시장 재승인 시 rule unpublish 안내 추가.",
    "old": '''    # E-1. dige(ranitidine) 사용 금지
    if "dige" in order_set:
        results.append({
            "level": "err",
            "message": "dige 사용 불가 — ranitidine 성분 시장 철수",
            "sub": "대체: reba(무코란) 또는 ppiiv(판타졸주사)",
            "source": "인수인계_2026년3월.md"
        })''',
    "new": '''    # E-1. dige(ranitidine) 시장 철수 (safety/warn)
    # session5: 문구 정리. 시장 재승인 시 rule unpublish 안내 추가.
    if "dige" in order_set:
        results.append({
            "level": "warn",
            "message": "dige 처방 불가 — ranitidine 국내 시장 철수",
            "sub": "대체: reba(무코란) 또는 ppiiv(판타졸주사). 시장 재승인 시 rule unpublish.",
            "source": "rules.json v0.3 dige_banned (2020년 NDMA 이슈 이후 철수)"
        })''',
}

ALL_PATCHES = [PATCH_1_PED_IV_BAN, PATCH_2_TAMIIV_INFO, PATCH_3_DIGE_BANNED]


# ═══════════════════════════════════════════════════════════════════
# 적용 로직
# ═══════════════════════════════════════════════════════════════════
def apply_patches(content: str) -> tuple[str, list[str]]:
    """
    content 에 ALL_PATCHES 를 순차 적용.
    반환: (수정된 content, 적용 결과 메시지 리스트)
    """
    messages = []
    for patch in ALL_PATCHES:
        name = patch["name"]
        marker = patch["marker_for_idempotency"]
        old = patch["old"]
        new = patch["new"]

        # 멱등성 체크: 이미 패치되어 있으면 skip
        if marker in content:
            messages.append(f"[SKIP] {name} — 이미 적용됨")
            continue

        # old 블록이 정확히 1회 등장하는지 검증
        count = content.count(old)
        if count == 0:
            raise ValueError(
                f"[FAIL] {name} — old block 매칭 0건. checker.py 가 변경됐을 수 있음."
            )
        if count > 1:
            raise ValueError(
                f"[FAIL] {name} — old block 매칭 {count}건 (예상 1건). 모호함."
            )

        # 적용
        content = content.replace(old, new, 1)
        messages.append(f"[OK]   {name} — 적용")

    return content, messages


def main(dry_run: bool, checker_path: Path, backup_path: Path) -> int:
    if not checker_path.exists():
        print(f"[FAIL] checker.py 없음: {checker_path}", file=sys.stderr)
        return 1

    original = checker_path.read_text(encoding="utf-8")
    print(f"[INFO] 원본 라인 수: {len(original.splitlines())}")

    try:
        patched, messages = apply_patches(original)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1

    for msg in messages:
        print(msg)

    if patched == original:
        print("[INFO] 변경 사항 없음 (전부 이미 적용됨)")
        return 0

    print(f"[INFO] 패치 후 라인 수: {len(patched.splitlines())}")

    if dry_run:
        print("[DRY] 파일 쓰기 생략")
        return 0

    shutil.copy2(checker_path, backup_path)
    print(f"[OK]   백업 생성: {backup_path}")

    checker_path.write_text(patched, encoding="utf-8")
    print(f"[OK]   patched: {checker_path}")
    print("[DONE] 패치 완료")
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="session5 checker.py minimal patch")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--checker-path", default=str(CHECKER_PATH))
    p.add_argument("--backup-path", default=str(BACKUP_PATH))
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    sys.exit(main(
        dry_run=args.dry_run,
        checker_path=Path(args.checker_path),
        backup_path=Path(args.backup_path),
    ))
