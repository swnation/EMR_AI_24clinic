"""
Session 4 checker.py patch 스크립트.

Usage (repo root 에서):
    python scripts/session4_checker_patch.py
    python scripts/session4_checker_patch.py --dry-run     # 수정 내용 미리보기
    python scripts/session4_checker_patch.py --revert      # 백업 복구

동작:
    1. app/checker.py 에 import 블록 추가 (rules_v2 + logging).
    2. run_check() 시그니처에 optional 파라미터 추가:
         vitals_context=None, patient_context=None
    3. run_check() 마지막 return 직전에 신규 rule 3개 호출 추가.
    4. 백업: app/checker.py.bak_session4 (최초 1회만 저장).

특성:
    - Idempotent: 이미 패치된 파일 다시 실행해도 "No changes" 로 종료.
    - Anchor 실패 시 RuntimeError + 파일 건드리지 않음.
    - --revert 로 백업에서 복구 가능.

설계:
    GPT 세션4 patch 스크립트의 구조 채택 + 내 rules_v2/ 모듈 구조에 맞게 재작성.
    (GPT 원본은 rules_v2/ 모듈 분리를 안 했기에 in-place 에 rule 함수까지 삽입했으나,
    본 버전은 rules_v2/ 를 활용하므로 checker.py 수정 폭이 훨씬 작음.)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


CHECKER_PATH = Path("app/checker.py")
BACKUP_PATH = Path("app/checker.py.bak_session4")
PATCH_MARKER = "# ── [session4] rules_v2 integration ──"


# ─────────────────────────────────────────────────────────────
# 삽입할 코드 블록
# ─────────────────────────────────────────────────────────────

IMPORT_BLOCK = '''
# ── [session4] rules_v2 integration ──
# 아래 import 는 세션 4 신규 rule (BST / 소아 제형 용량) 사용.
# 실패 시 신규 rule 만 비활성화되고 legacy rule 은 그대로 동작.
import logging as _s4_logging

try:
    from app.rules_v2.bst import check_bst_rules as _s4_check_bst_rules
    from app.rules_v2.pediatric_dose import (
        check_pediatric_formulation_dose as _s4_check_pediatric_formulation_dose,
        load_pediatric_drug_list as _s4_load_pediatric_drug_list,
    )
    _S4_RULES_AVAILABLE = True
except Exception as _e:   # pragma: no cover
    _S4_RULES_AVAILABLE = False
    _s4_logging.getLogger(__name__).warning(
        "[checker] rules_v2 import 실패. 신규 rule 비활성화. err=%s", _e,
    )

# 모듈 로드 시 1회 curated list 캐시.
_S4_PEDIATRIC_DRUG_LIST = None
if _S4_RULES_AVAILABLE:
    try:
        _S4_PEDIATRIC_DRUG_LIST = _s4_load_pediatric_drug_list()
    except Exception as _e:   # pragma: no cover
        _s4_logging.getLogger(__name__).warning(
            "[checker] pediatric drug list 로드 실패. 소아 rule skip. err=%s", _e,
        )

# vitals_context 미연결 로그를 1회만 남기기 위한 플래그.
_S4_LEGACY_WARNED = False
'''


CALL_BLOCK = '''
    # ── [session4] rules_v2 호출 ──
    if _S4_RULES_AVAILABLE:
        # BST 양방향 rule. vitals_context 미연결이면 내부에서 skip.
        if vitals_context is None:
            global _S4_LEGACY_WARNED
            if not _S4_LEGACY_WARNED:
                _s4_logging.getLogger(__name__).info(
                    "[checker] vitals_context 미연결 (legacy pipeline). BST rule skip."
                )
                _S4_LEGACY_WARNED = True
        else:
            results.extend(_s4_check_bst_rules(vitals_context, order_set))

        # 소아 제형 용량 rule. curated list 없으면 내부에서 skip.
        if _S4_PEDIATRIC_DRUG_LIST:
            _pc = patient_context or {}
            results.extend(_s4_check_pediatric_formulation_dose(
                orders=order_set,
                order_details=order_details,
                age_minor=_pc.get("age_minor") if isinstance(_pc, dict) else None,
                age_years=age,
                patient_type=patient_type,
                vitals_context=vitals_context,
                drug_list=_S4_PEDIATRIC_DRUG_LIST,
            ))

'''


# ─────────────────────────────────────────────────────────────
# Patch 로직
# ─────────────────────────────────────────────────────────────
def patch_text(text: str) -> str:
    """
    text (원본 checker.py) 를 받아 패치된 text 반환.
    이미 패치되어 있으면 그대로 반환.
    """
    if PATCH_MARKER in text:
        return text   # idempotent

    # ── [1] Import 블록 삽입 ──
    # 기존 import 들 바로 다음 (첫 번째 빈 줄 뒤) 에 삽입.
    # 최대한 안전하게: 파일 최상단 docstring 뒤, 기존 import 블록 뒤에 붙임.
    # 간단히: "from" 또는 "import" 로 시작하는 연속 라인의 마지막 다음 위치.
    lines = text.splitlines(keepends=True)
    last_import_idx = -1
    in_block = False
    for i, ln in enumerate(lines):
        stripped = ln.lstrip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            last_import_idx = i
            in_block = True
        elif in_block and stripped == "" and last_import_idx >= 0:
            # import 블록이 끝난 지점 (첫 빈 줄).
            break
    if last_import_idx < 0:
        raise RuntimeError(
            "checker.py 안에서 import 블록 anchor 를 찾지 못함."
        )
    insert_at = last_import_idx + 1
    patched_lines = (
        lines[:insert_at]
        + [IMPORT_BLOCK + "\n"]
        + lines[insert_at:]
    )
    text = "".join(patched_lines)

    # ── [2] run_check 시그니처 확장 ──
    # 정규식: def run_check( ... ) -> List[Dict]: 또는 def run_check( ... ):
    sig_pat = re.compile(
        r"def\s+run_check\(\s*(?P<args>[^)]*)\)\s*(?:->\s*List\[Dict\]\s*)?:",
        re.MULTILINE,
    )
    m = sig_pat.search(text)
    if not m:
        raise RuntimeError("run_check() 시그니처 anchor 를 찾지 못함.")
    args = m.group("args")
    if "vitals_context" not in args:
        new_args = args.rstrip().rstrip(",")
        if new_args.strip():
            new_args += ","
        new_args += " vitals_context=None, patient_context=None"
        text = text[: m.start("args")] + new_args + text[m.end("args"):]

    # ── [3] run_check 마지막 `return results` 앞에 신규 rule 호출 삽입 ──
    # run_check 함수 범위 내에서 마지막 `    return results` 를 찾음.
    # 가장 단순한 방법: 파일 전체의 마지막 "    return results" 를 anchor 로.
    # checker.py 는 run_check 가 하나이므로 안전.
    ret_anchor = "    return results"
    last_ret_idx = text.rfind(ret_anchor)
    if last_ret_idx < 0:
        raise RuntimeError("'    return results' anchor 를 찾지 못함.")
    text = text[:last_ret_idx] + CALL_BLOCK + text[last_ret_idx:]

    return text


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────
def main(argv: list) -> int:
    parser = argparse.ArgumentParser(
        description="Apply session 4 rules_v2 integration to app/checker.py."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="변경 내용만 stdout 으로 출력. 파일은 건드리지 않음.",
    )
    parser.add_argument(
        "--revert", action="store_true",
        help=f"{BACKUP_PATH} 에서 복구.",
    )
    args = parser.parse_args(argv)

    if args.revert:
        if not BACKUP_PATH.exists():
            print(f"[ERROR] 백업 파일 없음: {BACKUP_PATH}", file=sys.stderr)
            return 1
        original = BACKUP_PATH.read_text(encoding="utf-8")
        CHECKER_PATH.write_text(original, encoding="utf-8")
        print(f"[OK] {CHECKER_PATH} 를 {BACKUP_PATH} 로부터 복구.")
        return 0

    if not CHECKER_PATH.exists():
        print(f"[ERROR] {CHECKER_PATH} 없음. repo root 에서 실행하는지 확인.", file=sys.stderr)
        return 1

    original = CHECKER_PATH.read_text(encoding="utf-8")
    try:
        patched = patch_text(original)
    except RuntimeError as e:
        print(f"[ERROR] 패치 실패 (anchor 문제): {e}", file=sys.stderr)
        return 2

    if patched == original:
        print("[SKIP] 이미 패치되어 있음. 변경 없음.")
        return 0

    if args.dry_run:
        # 단순 diff 요약
        print("[DRY RUN] 변경될 파일:", CHECKER_PATH)
        print(f"  원본 길이: {len(original)} chars")
        print(f"  패치 후  : {len(patched)} chars  (+{len(patched) - len(original)})")
        print(f"  삽입 marker: {PATCH_MARKER!r}")
        print("\n--- 패치 후 content (처음 80줄) ---")
        for i, ln in enumerate(patched.splitlines()[:80], 1):
            print(f"{i:3d}  {ln}")
        return 0

    # 백업
    if not BACKUP_PATH.exists():
        BACKUP_PATH.write_text(original, encoding="utf-8")
        print(f"[OK] 백업 생성: {BACKUP_PATH}")
    else:
        print(f"[INFO] 백업 이미 존재: {BACKUP_PATH} (덮어쓰지 않음)")

    CHECKER_PATH.write_text(patched, encoding="utf-8")
    print(f"[OK] 패치 적용: {CHECKER_PATH}")
    print(f"[INFO] 롤백: python scripts/session4_checker_patch.py --revert")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
