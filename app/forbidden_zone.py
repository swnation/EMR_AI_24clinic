"""
Forbidden zone 자동 검증 (Capture-level PHI 방어선)

참조 문서:
    - decision-2026-04-21-capture-regions-and-rules.md §2 (PHI forbidden zone)
    - design/system-overview-v3.md §11.7

원칙:
    - 마스킹이 아니라 "애초에 수집 안 함" 을 코드 레벨에서 강제.
    - 캡처 bbox 가 forbidden zone 과 겹치면 즉시 실패 (RuntimeError).
    - 실패 시 조용히 넘어가지 않음. 로그 저장.

사용법:
    from forbidden_zone import assert_regions_safe, load_forbidden_regions

    regions = json.load(open("ocr/regions.json"))
    forbidden = load_forbidden_regions()
    assert_regions_safe(regions, forbidden)   # 문제 있으면 RuntimeError

데이터 파일:
    ocr/forbidden_regions.json
    - 진료실 PC 실측 후 채워야 하는 placeholder 상태로 시작.
    - placeholder 상태에서는 assertion 이 skip 되지만 경고 출력.

Capture-level vs Transmission-level (Decision §2 마지막 항):
    - 이 모듈: Capture-level forbidden zone (캡처 자체 금지).
    - Transmission-level allowlist (export 시 제외)는 export_dataset.py 담당.
"""
import json
import os
import sys
from datetime import datetime


# ─────────────────────────────────────────────────────────────
# 파일 경로
# ─────────────────────────────────────────────────────────────
_DIR = os.path.dirname(__file__)
FORBIDDEN_PATH = os.path.join(_DIR, "forbidden_regions.json")
VIOLATION_LOG_PATH = os.path.join(_DIR, "forbidden_violations.log")


# ─────────────────────────────────────────────────────────────
# bbox 유틸
# ─────────────────────────────────────────────────────────────
def _extract_bbox(d):
    """딕셔너리에서 {x1,y1,x2,y2} 튜플 추출 (다른 메타 필드 무시)."""
    return (d["x1"], d["y1"], d["x2"], d["y2"])


def is_valid_bbox(d) -> bool:
    """
    bbox 가 유효한가? (Patch A 신규)

    유효 조건: x2 > x1, y2 > y1 (0-size 또는 뒤집힘 금지).
    invalid bbox 는 overlap 검사 공식이 오동작하므로 반드시 사전 차단.
    """
    try:
        x1, y1, x2, y2 = _extract_bbox(d)
    except (KeyError, TypeError):
        return False
    return x2 > x1 and y2 > y1


def bboxes_overlap(a, b) -> bool:
    """
    두 bbox 가 겹치는지 판정. bbox = {x1,y1,x2,y2}.
    겹치지 않는 조건 중 하나라도 참이면 False.

    사전 조건: a, b 모두 is_valid_bbox() 통과. invalid bbox 넘기면 ValueError.
    Patch A+: 명시적 raise (python -O 옵션에서도 안전). assert 는 -O 에서 제거됨.
    """
    if not is_valid_bbox(a):
        raise ValueError(f"invalid bbox (a): {a}")
    if not is_valid_bbox(b):
        raise ValueError(f"invalid bbox (b): {b}")
    ax1, ay1, ax2, ay2 = _extract_bbox(a)
    bx1, by1, bx2, by2 = _extract_bbox(b)
    if ax2 <= bx1 or ax1 >= bx2:
        return False
    if ay2 <= by1 or ay1 >= by2:
        return False
    return True


# ─────────────────────────────────────────────────────────────
# 로드 / 판정
# ─────────────────────────────────────────────────────────────
def load_forbidden_regions(path=FORBIDDEN_PATH) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"forbidden_regions.json 이 없다: {path}\n"
            f"최초 실행 시 placeholder 파일을 만들려면 init_placeholder() 호출."
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_placeholder_state(forbidden: dict) -> bool:
    """
    모든 forbidden region 이 placeholder 인 상태 (실측 전).
    이 경우 assertion 을 skip 하되 경고 출력.
    """
    return forbidden.get("_status") == "placeholder_pending_measurement"


def find_violations(regions: dict, forbidden: dict) -> list:
    """
    regions(캘리브레이션된 캡처 영역) 중 forbidden zone 과 겹치는 쌍 탐지.
    Returns: [(region_key, forbidden_key), ...]

    사전 조건: bbox 모두 is_valid_bbox 통과 (assert_regions_safe 에서 검증됨).
    """
    violations = []
    for r_key, r_val in regions.items():
        if r_key.startswith("_") or not isinstance(r_val, dict):
            continue
        if "x1" not in r_val:  # bbox 형태 아닌 엔트리 skip
            continue
        if not is_valid_bbox(r_val):
            continue  # invalid 는 상위에서 raise; 방어적 skip
        for f_key, f_val in forbidden.items():
            if f_key.startswith("_") or not isinstance(f_val, dict):
                continue
            if "x1" not in f_val:
                continue
            if f_val.get("_placeholder"):
                continue  # 개별 placeholder 항목 skip (active 상태면 상위에서 raise)
            if not is_valid_bbox(f_val):
                continue
            if bboxes_overlap(r_val, f_val):
                violations.append((r_key, f_key))
    return violations


def _log_violations(violations, regions, forbidden):
    with open(VIOLATION_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n--- {datetime.now().isoformat(timespec='seconds')} ---\n")
        for r_key, f_key in violations:
            r_bbox = _extract_bbox(regions[r_key])
            f_bbox = _extract_bbox(forbidden[f_key])
            f.write(f"  {r_key} {r_bbox}  overlaps  {f_key} {f_bbox}\n")


# ─────────────────────────────────────────────────────────────
# _status enum (Patch A+)
# ─────────────────────────────────────────────────────────────
ALLOWED_FORBIDDEN_STATUS = frozenset({
    "active",                          # 운영 — 모든 필드 실측 완료
    "placeholder_pending_measurement", # 최초 상태 — 전체 placeholder
    "partial_for_development_only",    # 개발 전용 — strict 모드에서 금지
})


def _assert_valid_status(forbidden: dict, strict: bool = True):
    """
    _status 값이 enum 에 속하는지 검증 (Patch A+).

    오타 하나로 방어선이 꺼지는 상황 방지:
      예: _status="acitve" 하나만으로 active 아닌데 placeholder 도 아닌 "이상 상태" 가 됨.
          기존 로직상 이 경우 _assert_no_partial_placeholder_when_active 를 통과하고
          is_placeholder_state 도 False 라 find_violations 로 직행.
          그런데 개별 _placeholder 엔트리는 skip 되므로 해당 PHI 영역 검증이 조용히 꺼짐.
    """
    status = forbidden.get("_status")
    if status not in ALLOWED_FORBIDDEN_STATUS:
        raise RuntimeError(
            f"[forbidden_zone] _status 값이 유효하지 않음: {status!r}\n"
            f"  허용 값: {sorted(ALLOWED_FORBIDDEN_STATUS)}\n"
            f"  오타 확인 (예: 'acitve' → 'active')."
        )
    if status == "partial_for_development_only" and strict:
        raise RuntimeError(
            f"[forbidden_zone] _status='partial_for_development_only' 는 "
            f"strict 모드에서 허용 안 됨. 운영 capture 에서는 반드시 'active'."
        )


def _assert_all_bboxes_valid(regions: dict, label: str):
    """
    regions 내 모든 bbox 엔트리가 is_valid_bbox 를 통과하는지 검증 (Patch A).
    invalid bbox 가 하나라도 있으면 PHI 방어선이 신뢰 불가 → 즉시 raise.
    """
    invalid = []
    for k, v in regions.items():
        if k.startswith("_") or not isinstance(v, dict):
            continue
        if "x1" not in v:
            continue
        # placeholder 는 0,0,0,0 이므로 valid 체크 skip (active 체크에서 별도 처리)
        if v.get("_placeholder"):
            continue
        if not is_valid_bbox(v):
            invalid.append((k, _extract_bbox(v)))
    if invalid:
        raise RuntimeError(
            f"[forbidden_zone] {label} 에 invalid bbox 가 있다 "
            f"(x2>x1, y2>y1 위반): {invalid}. 해당 항목 재캘리브레이션 필요."
        )


def _assert_no_partial_placeholder_when_active(forbidden: dict):
    """
    _status == active 인데 개별 필드의 _placeholder: true 가 남아 있으면 실패 (Patch A).

    부분 활성화 상태는 가장 위험함 — 한 필드만 placeholder 로 남아있어도
    그 영역의 PHI 방어선이 조용히 꺼진 상태가 됨. Decision §2 "PHI 수집 안 함을
    코드 레벨에서 강제" 원칙과 충돌.

    의도적으로 점진 활성화하려면 _status 를 "partial_for_development_only" 등
    별도 값으로 명시적으로 선언할 것.
    """
    if forbidden.get("_status") != "active":
        return
    stale = []
    for k, v in forbidden.items():
        if k.startswith("_") or not isinstance(v, dict):
            continue
        if v.get("_placeholder"):
            stale.append(k)
    if stale:
        raise RuntimeError(
            f"[forbidden_zone] _status=active 인데 _placeholder 플래그가 남은 필드: {stale}. "
            f"해당 필드 bbox 를 실측 값으로 채운 뒤 _placeholder 를 제거할 것. "
            f"의도적 부분 활성화라면 _status 를 다른 값으로 바꿀 것."
        )


def assert_regions_safe(regions: dict, forbidden: dict = None, strict: bool = True):
    """
    캡처 영역이 forbidden zone 과 겹치지 않음을 보장.

    Args:
        regions: calibrate.py 가 만든 regions.json 내용.
        forbidden: forbidden_regions.json 내용 (None 이면 자동 로드).
        strict: placeholder 상태를 에러로 처리할지. 운영 capture 에서는 반드시 True.
                **strict=False 는 CLI selftest / dev mode 전용.**

    Raises:
        RuntimeError: 겹침 발견, invalid bbox, active+placeholder 혼재, 또는
                      strict=True 상태에서 placeholder-only forbidden 인 경우.
    """
    if forbidden is None:
        forbidden = load_forbidden_regions()

    # Patch A+: _status enum 검증. 오타 / 비정상 상태 값 차단.
    _assert_valid_status(forbidden, strict=strict)

    # Patch A: bbox validity (regions / forbidden 양쪽)
    _assert_all_bboxes_valid(regions, "regions")
    _assert_all_bboxes_valid(forbidden, "forbidden_regions")

    # Patch A: active 상태에서 개별 placeholder 잔존 시 실패
    _assert_no_partial_placeholder_when_active(forbidden)

    if is_placeholder_state(forbidden):
        msg = (
            "[forbidden_zone] forbidden_regions.json 이 placeholder 상태.\n"
            "  진료실 PC 에서 의사랑 하단 PHI strip 의 각 필드 bbox 를 실측한 뒤 채워야 한다.\n"
            "  현재는 assertion 을 skip 한다."
        )
        if strict:
            raise RuntimeError(msg + "\n  strict=True 이므로 실행 중단.")
        print(msg, file=sys.stderr)
        return

    violations = find_violations(regions, forbidden)
    if violations:
        _log_violations(violations, regions, forbidden)
        details = ", ".join(f"{r}↔{f}" for r, f in violations)
        raise RuntimeError(
            f"[forbidden_zone] 캡처 영역이 PHI 금지구역과 겹친다: {details}\n"
            f"  해당 영역을 재캘리브레이션하거나 forbidden_regions 재확인 필요.\n"
            f"  로그: {VIOLATION_LOG_PATH}"
        )


# ─────────────────────────────────────────────────────────────
# Placeholder 초기화 (최초 1회)
# ─────────────────────────────────────────────────────────────
def init_placeholder(path=FORBIDDEN_PATH, overwrite=False):
    """
    forbidden_regions.json 을 placeholder 상태로 생성.
    진료실 PC 에서 각 필드의 bbox 를 실측한 뒤 `x1,y1,x2,y2` 값을 채우고
    `_placeholder: true` 를 제거하면 활성화된다.

    실측 대상 필드 (의사랑 하단 PHI strip 기준):
        - patient_name      이름
        - patient_rrn       주민등록번호
        - insurance_id      보험번호
        - phone             전화번호
        - (옵션) 하단 strip 좌측/중앙 통째 bbox
    """
    if os.path.exists(path) and not overwrite:
        raise FileExistsError(f"{path} 이미 존재. overwrite=True 로 재생성 가능.")

    placeholder = {
        "_schema_version": 1,
        "_status": "placeholder_pending_measurement",
        "_note": (
            "진료실 PC 에서 의사랑 하단 PHI strip 의 각 필드 bbox 를 실측한 뒤 값을 채우고 "
            "_status 를 'active' 로, 각 필드의 _placeholder 를 false 또는 제거할 것."
        ),
        "patient_name":  {"x1": 0, "y1": 0, "x2": 0, "y2": 0, "_placeholder": True,
                          "_desc": "환자 이름 칸"},
        "patient_rrn":   {"x1": 0, "y1": 0, "x2": 0, "y2": 0, "_placeholder": True,
                          "_desc": "주민등록번호 칸"},
        "insurance_id":  {"x1": 0, "y1": 0, "x2": 0, "y2": 0, "_placeholder": True,
                          "_desc": "보험번호 칸"},
        "phone":         {"x1": 0, "y1": 0, "x2": 0, "y2": 0, "_placeholder": True,
                          "_desc": "전화번호 칸"},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(placeholder, f, indent=2, ensure_ascii=False)
    print(f"[forbidden_zone] placeholder 생성: {path}")


# ─────────────────────────────────────────────────────────────
# 셀프 테스트
# ─────────────────────────────────────────────────────────────
def _selftest():
    print("=" * 60)
    print("  forbidden_zone 셀프 테스트")
    print("=" * 60)

    # bbox overlap 로직 단위 테스트
    print("\n[1] bbox overlap 로직")
    cases = [
        # (a, b, expected, label)
        ({"x1":0,"y1":0,"x2":10,"y2":10},
         {"x1":5,"y1":5,"x2":15,"y2":15}, True,  "부분 겹침"),
        ({"x1":0,"y1":0,"x2":10,"y2":10},
         {"x1":10,"y1":0,"x2":20,"y2":10}, False, "가장자리만 접촉 (겹침 아님)"),
        ({"x1":0,"y1":0,"x2":10,"y2":10},
         {"x1":20,"y1":20,"x2":30,"y2":30}, False, "완전 분리"),
        ({"x1":0,"y1":0,"x2":100,"y2":100},
         {"x1":10,"y1":10,"x2":20,"y2":20}, True,  "완전 포함"),
        ({"x1":0,"y1":0,"x2":10,"y2":10},
         {"x1":5,"y1":20,"x2":15,"y2":30}, False, "x축 겹침만, y축 분리"),
    ]
    for a, b, expected, label in cases:
        got = bboxes_overlap(a, b)
        status = "✓" if got == expected else "✗"
        print(f"    {status} {label}: expected={expected}, got={got}")
        assert got == expected, f"{label} 실패"

    # placeholder 상태 판정
    print("\n[2] placeholder 상태 판정")
    ph = {"_status": "placeholder_pending_measurement"}
    ac = {"_status": "active"}
    assert is_placeholder_state(ph) is True
    assert is_placeholder_state(ac) is False
    print("    ✓ placeholder 감지 OK")

    # 실제 위반 탐지
    print("\n[3] 위반 탐지")
    regions_safe = {
        "_schema_version": 2,
        "symptoms":  {"tier":"tier1","x1":100,"y1":100,"x2":500,"y2":300},
        "dx":        {"tier":"tier1","x1":100,"y1":350,"x2":500,"y2":500},
    }
    regions_bad = {
        "symptoms":         {"tier":"tier1","x1":100,"y1":100,"x2":500,"y2":300},
        "patient_id_region":{"tier":"tier2_5","x1":0,"y1":900,"x2":200,"y2":950},
    }
    forbidden_active = {
        "_status": "active",
        "patient_name":  {"x1":180,"y1":895,"x2":280,"y2":955},  # 환자번호 영역과 겹침
        "patient_rrn":   {"x1":280,"y1":895,"x2":430,"y2":955},
    }
    v1 = find_violations(regions_safe, forbidden_active)
    v2 = find_violations(regions_bad, forbidden_active)
    print(f"    안전 영역: violations = {v1}")
    print(f"    위험 영역: violations = {v2}")
    assert v1 == []
    assert len(v2) == 1 and v2[0] == ("patient_id_region", "patient_name")
    print("    ✓ 탐지 로직 OK")

    # assert_regions_safe 동작
    print("\n[4] assert_regions_safe")
    try:
        assert_regions_safe(regions_safe, forbidden_active)
        print("    ✓ 안전 영역: 통과")
    except RuntimeError:
        raise AssertionError("안전 영역인데 raise 됨")
    try:
        assert_regions_safe(regions_bad, forbidden_active)
        raise AssertionError("위반이 있는데 raise 안 됨")
    except RuntimeError as e:
        print(f"    ✓ 위반 영역: RuntimeError 발생 (예상대로)")

    # placeholder 처리
    print("\n[5] placeholder 상태 처리 (strict=False)")
    ph_only = {
        "_status": "placeholder_pending_measurement",
        "patient_name": {"x1":0,"y1":0,"x2":0,"y2":0,"_placeholder":True},
    }
    try:
        assert_regions_safe(regions_bad, ph_only, strict=False)
        print("    ✓ strict=False 시 skip (경고 출력)")
    except RuntimeError:
        raise AssertionError("strict=False 인데 raise 됨")

    # Patch A 신규: active 상태에서 개별 placeholder 잔존
    print("\n[6] Patch A: active 상태 + 개별 placeholder 잔존 (실패해야 함)")
    mixed_forbidden = {
        "_status": "active",
        "patient_name": {"x1":180,"y1":895,"x2":280,"y2":955},  # 실측됨
        "phone":        {"x1":0,"y1":0,"x2":0,"y2":0,"_placeholder":True},  # 깜빡 남음
    }
    try:
        assert_regions_safe(regions_safe, mixed_forbidden)
        raise AssertionError("active + placeholder 혼재인데 통과함")
    except RuntimeError as e:
        msg = str(e)
        assert "phone" in msg
        print(f"    ✓ RuntimeError 발생: {msg[:100]}...")

    # Patch A 신규: invalid bbox (x2 < x1)
    print("\n[7] Patch A: invalid bbox (x2 <= x1 또는 y2 <= y1)")
    regions_invalid = {
        "broken": {"tier":"tier1", "x1":500, "y1":100, "x2":100, "y2":50},  # 뒤집힘
    }
    try:
        assert_regions_safe(regions_invalid, forbidden_active)
        raise AssertionError("invalid bbox 인데 통과함")
    except RuntimeError as e:
        print(f"    ✓ RuntimeError 발생: {str(e)[:100]}...")

    # is_valid_bbox 직접 테스트
    print("\n[8] is_valid_bbox")
    assert is_valid_bbox({"x1":0,"y1":0,"x2":10,"y2":10}) is True
    assert is_valid_bbox({"x1":0,"y1":0,"x2":0,"y2":10}) is False     # 0 width
    assert is_valid_bbox({"x1":0,"y1":0,"x2":10,"y2":0}) is False     # 0 height
    assert is_valid_bbox({"x1":10,"y1":0,"x2":0,"y2":10}) is False    # x 뒤집힘
    assert is_valid_bbox({"x1":0,"y1":10,"x2":10,"y2":0}) is False    # y 뒤집힘
    print("    ✓ valid / 0-size / 뒤집힘 모두 올바르게 판정")

    # Patch A+ 신규: _status 오타 방어
    print("\n[9] Patch A+: _status 오타 ('acitve') 차단")
    typo_forbidden = {
        "_status": "acitve",   # 오타 — 기존 로직이었다면 phone placeholder 를 skip
        "patient_name": {"x1":180,"y1":895,"x2":280,"y2":955},
        "phone":        {"x1":0,"y1":0,"x2":0,"y2":0,"_placeholder":True},
    }
    try:
        assert_regions_safe(regions_safe, typo_forbidden)
        raise AssertionError("_status 오타인데 통과함 → PHI 방어선 OFF 리스크")
    except RuntimeError as e:
        msg = str(e)
        assert "acitve" in msg or "_status" in msg
        print(f"    ✓ RuntimeError: {msg[:100]}...")

    # Patch A+ 신규: partial_for_development_only 는 strict 에서 실패
    print("\n[10] Patch A+: partial_for_development_only 는 strict 에서 금지")
    partial_forbidden = {
        "_status": "partial_for_development_only",
        "patient_name": {"x1":180,"y1":895,"x2":280,"y2":955},
        "phone":        {"x1":0,"y1":0,"x2":0,"y2":0,"_placeholder":True},
    }
    try:
        assert_regions_safe(regions_safe, partial_forbidden, strict=True)
        raise AssertionError("partial_for_development_only 가 strict 에서 통과함")
    except RuntimeError as e:
        print(f"    ✓ strict=True: RuntimeError (예상대로)")
    # strict=False 에서는 통과 (dev mode)
    try:
        assert_regions_safe(regions_safe, partial_forbidden, strict=False)
        print(f"    ✓ strict=False: 통과 (dev mode)")
    except RuntimeError as e:
        raise AssertionError(f"strict=False 인데 raise: {e}")

    print("\n모든 테스트 통과.")


if __name__ == "__main__":
    _selftest()
