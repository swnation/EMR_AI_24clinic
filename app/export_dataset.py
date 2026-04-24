"""
Export: 운영 DB 레코드 → OCR 분석 데이터셋 (집 PC 전송용)

참조 문서:
    - decision-2026-04-21-patient-identifier-policy.md §1 (2-Tier 저장), §6 (Export 안전장치)
    - design/system-overview-v3.md §11.5.3

5단계 안전장치 (Decision §6):
    1. 운영 DB 원본을 그대로 복사하지 않는다.
    2. Allowlist 필드만 새 객체로 재구성한다.
    3. 금지 필드가 하나라도 섞이면 즉시 실패 (fail-fast RuntimeError).
    4. Export 결과 필드 목록 (manifest) 을 남긴다.
    5. 샘플 1건 사람 검토  ← 코드 범위 밖 (SOP 후속 작업).

Patch A (2026-04-24):
    - strict_input=True 에서 **unknown top-level field** 도 즉시 실패 (이전 구현은 조용히 drop).
      "허용 필드만" 원칙을 ALLOWED 기준으로 enforce. 블랙리스트(FORBIDDEN) 는 이중 방어용.
    - strict_input=False 옵션 제거 → 별도 함수 sanitize_operational_record_for_dataset()
      로 이름 변경. "위험한 ETL 용도" 임을 함수명에 명시.

사용법:
    from export_dataset import export_records, write_manifest

    ops_records = [...]  # 운영 DB 에서 이미 ETL 거쳐 allowlist 필드만 남긴 레코드들
    exported = export_records(ops_records)
    write_manifest(exported, "export_2026-04-24/manifest.json")

    # 만약 운영 DB 원본을 한번에 정리해야 한다면 (주의해서):
    # cleaned = sanitize_operational_record_for_dataset(ops_record)
"""
import json
import os
from datetime import datetime
from copy import deepcopy


# ─────────────────────────────────────────────────────────────
# Allowlist / Forbidden 정의
#   Decision §1 기준:
#     분석 데이터셋 포함: session_id, age_major/minor/flags, sex, chart_date,
#                         clinical_regions, vitals_context
#     분석 데이터셋 제외: patient_key, patient_no, age_years, doctor_code,
#                         captured_at, statement_context, patient_id_region
# ─────────────────────────────────────────────────────────────
ALLOWED_TOP_LEVEL = frozenset({
    "session_id",
    "age_major",
    "age_minor",
    "age_flags",
    "sex",
    "chart_date",
    "clinical_regions",   # {symptoms, special, dx, orders} 서브키
    "vitals_context",     # {BT, BW, BP1, BP2, PR, BST}
})

# Top-level 에서만 forbidden 으로 취급할 키 (컨테이너 이름 포함).
# 운영 DB 원본을 그대로 넣는 실수를 input 단계에서 거부하는 용도.
FORBIDDEN_TOP_LEVEL = frozenset({
    "patient_key",
    "patient_no",
    "age_years",
    "doctor_code",
    "captured_at",
    "statement_context",
    "patient_id_region",
    "aux",                # Decision §18.1 운영 DB 쪽 컨테이너
    "patient_context",    # 안에 patient_no/age_years 섞여 있을 가능성
    "encounter_meta",     # 안에 doctor_code/captured_at 섞여 있을 가능성
})

# Any-depth forbidden (Patch A+ 신규).
# Nested value smuggling 방어 — allowed top-level 안에 PHI key 가 숨어 있어도 차단.
# 예:
#   {"sex": {"patient_no": "C-00123"}}       # sex 는 allowed 지만 내부는 PHI
#   {"age_flags": [{"phone": "010-..."}]}    # list 내부 dict
FORBIDDEN_KEYS_ANY_DEPTH = frozenset({
    # Decision §1 운영 DB 전용 필드 — depth 무관 금지
    "patient_key",
    "patient_no",
    "age_years",
    "doctor_code",
    "captured_at",
    "patient_id_region",
    "statement_context",
    # 흔한 PHI key 이름 — 어떤 depth 에서든 위험
    "name",
    "patient_name",
    "rrn",
    "phone",
    "insurance_id",
})

# clinical_regions 의 허용 서브키 (Decision §5.2)
ALLOWED_CLINICAL_REGION_KEYS = frozenset({"symptoms", "special", "dx", "orders"})

# vitals_context 의 허용 서브키 (D3 §3)
ALLOWED_VITALS_KEYS = frozenset({
    "BT", "BW", "BP1", "BP2", "PR", "BST",
    # 정규화 alias 도 허용
    "bt", "bw", "sbp", "dbp", "pr", "bst",
})


# ─────────────────────────────────────────────────────────────
# 변환 + 검증
# ─────────────────────────────────────────────────────────────
class ExportError(RuntimeError):
    """Export 안전장치 위반. 즉시 실패."""


def _validate_allowlist(obj, path: str = ""):
    """
    재귀 순회. 모든 depth 에서 FORBIDDEN_KEYS_ANY_DEPTH 감지.
    dict 뿐 아니라 list 내부 dict 도 검사.

    Patch A+ (2026-04-24): 이전 구현은 top-level 에서만 forbidden 을 체크해서
    아래 같은 nested smuggling 이 통과했음:
        {"sex": {"patient_no": "C-00123"}}       # sex 는 allowed 지만 내부 PHI
        {"age_flags": [{"phone": "010-..."}]}    # list 안의 dict 가 PHI

    이제 depth 무관 차단. list 재귀 포함.
    """
    if isinstance(obj, dict):
        for key, val in obj.items():
            current = f"{path}.{key}" if path else key
            if key in FORBIDDEN_KEYS_ANY_DEPTH:
                raise ExportError(
                    f"Export 실패 (Step 3, any-depth): "
                    f"forbidden key '{current}' 감지. "
                    f"allowlist 필드 내부에 숨어 있어도 차단."
                )
            _validate_allowlist(val, current)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _validate_allowlist(item, f"{path}[{i}]")
    # 그 외 (str, int, float, None 등 scalar) 은 검사 불필요


def _build_clean_record(source: dict) -> dict:
    """
    Step 2: allowlist 필드만 새 객체로 재구성.
    Step 3 의 fail-fast 검증을 위해 내부 구조도 sub-key 필터링.
    """
    result = {}

    for field in ALLOWED_TOP_LEVEL:
        if field not in source:
            continue
        value = source[field]

        if field == "clinical_regions" and isinstance(value, dict):
            cleaned = {
                k: deepcopy(v)
                for k, v in value.items()
                if k in ALLOWED_CLINICAL_REGION_KEYS
            }
            extra = set(value.keys()) - ALLOWED_CLINICAL_REGION_KEYS
            if extra:
                raise ExportError(
                    f"Export 실패 (Step 3): clinical_regions 에 허용되지 않은 서브키: {extra}"
                )
            result[field] = cleaned

        elif field == "vitals_context" and isinstance(value, dict):
            cleaned = {
                k: deepcopy(v)
                for k, v in value.items()
                if k in ALLOWED_VITALS_KEYS
            }
            extra = set(value.keys()) - ALLOWED_VITALS_KEYS
            if extra:
                raise ExportError(
                    f"Export 실패 (Step 3): vitals_context 에 허용되지 않은 서브키: {extra}"
                )
            result[field] = cleaned

        else:
            result[field] = deepcopy(value)

    return result


def export_record(operational_record: dict) -> dict:
    """
    단일 레코드를 분석 데이터셋 형식으로 변환 (strict).

    Patch A: strict 가 상수화됨. 입력에 ALLOWED_TOP_LEVEL 외의 필드가
    **하나라도** 있으면 실패. forbidden 이든 unknown 이든 상관없이.
    조용히 필터링하는 동작은 별도 함수 sanitize_operational_record_for_dataset() 로 분리.

    Args:
        operational_record: 이미 ETL 로 분석용 필드만 남긴 dataset-ready 레코드.

    Steps:
        1. 원본 복사 금지 → 입력 검증 (ALLOWED 외 필드 있으면 실패).
        2. allowlist 기반 재구성.
        3. forbidden field 가 남으면 fail-fast (이중 방어).
    """
    # Step 1 (Patch A 강화): 입력이 dataset-ready 가 아니면 거부.
    # 이전 구현은 FORBIDDEN_TOP_LEVEL 만 체크했으나, 이러면 "name", "phone" 같은
    # unknown 필드가 조용히 drop 됨. fail-fast 철학 위반.
    unexpected = set(operational_record.keys()) - ALLOWED_TOP_LEVEL
    if unexpected:
        # FORBIDDEN 에 속한 것 / 완전 unknown 을 구분해 더 친절한 메시지
        forbidden_hit = unexpected & FORBIDDEN_TOP_LEVEL
        other_unknown = unexpected - FORBIDDEN_TOP_LEVEL
        parts = []
        if forbidden_hit:
            parts.append(f"운영 DB 전용 필드 포함 = {sorted(forbidden_hit)}")
        if other_unknown:
            parts.append(f"allowlist 에 없는 unknown 필드 = {sorted(other_unknown)}")
        raise ExportError(
            "Export 실패 (Step 1, fail-fast): "
            + "; ".join(parts)
            + ". 분석용 ETL 파이프라인을 거친 레코드만 전달할 것. "
            "운영 DB 원본을 조용히 정리할 필요가 있다면 "
            "sanitize_operational_record_for_dataset() 사용."
        )

    # Step 2: 새 객체에 allowlist 만 복사
    clean = _build_clean_record(operational_record)

    # Step 3: 이중 방어 — 중첩 레벨의 forbidden key 감지
    _validate_allowlist(clean)

    # 추가 sanity: session_id 필수
    if "session_id" not in clean:
        raise ExportError("Export 실패: session_id 누락.")

    return clean


def sanitize_operational_record_for_dataset(operational_record: dict) -> dict:
    """
    **위험 함수**. 운영 DB 원본 레코드에서 allowlist 필드만 조용히 뽑아 dataset-ready 로 변환.

    용도: 운영 DB 에서 SELECT 쿼리로 dataset 형식을 직접 만들 수 없는 예외 상황에서만.
    예: one-off migration, backfill, legacy 스키마 마이그레이션.

    **이 함수의 결과를 자동화 파이프라인에 그대로 연결하지 말 것.**
    결과는 반드시 사람이 확인 후 export_record() 에 다시 넣어 이중 검증.

    Patch A 이전의 export_record(strict_input=False) 와 동일 동작이지만, 이름을 바꿔
    실수로 운영 경로에 들어가는 것을 방지.
    """
    clean = _build_clean_record(operational_record)
    _validate_allowlist(clean)
    return clean


def export_records(operational_records: list) -> list:
    """여러 레코드 일괄 변환. 하나라도 실패하면 전체 중단."""
    out = []
    for idx, rec in enumerate(operational_records):
        try:
            out.append(export_record(rec))
        except ExportError as e:
            raise ExportError(f"[index={idx}, session_id={rec.get('session_id')}] {e}") from e
    return out


# ─────────────────────────────────────────────────────────────
# Manifest (Step 4)
# ─────────────────────────────────────────────────────────────
def build_manifest(exported_records: list) -> dict:
    """
    Export 결과 필드 목록과 메타 정보 생성.
    실측 레코드의 필드 교집합/합집합 을 함께 기록해 이상 레코드 탐지에 쓴다.
    """
    if not exported_records:
        top_fields = set()
    else:
        top_fields = set(exported_records[0].keys())
        for r in exported_records[1:]:
            top_fields &= set(r.keys())

    all_fields_observed = set()
    for r in exported_records:
        all_fields_observed.update(r.keys())

    return {
        "export_timestamp": datetime.now().isoformat(timespec="seconds"),
        "record_count": len(exported_records),
        "schema_version": 1,
        "allowed_top_level_fields": sorted(ALLOWED_TOP_LEVEL),
        "forbidden_top_level_fields": sorted(FORBIDDEN_TOP_LEVEL),
        "fields_in_all_records": sorted(top_fields),
        "fields_in_any_record": sorted(all_fields_observed),
        "unexpected_fields": sorted(all_fields_observed - ALLOWED_TOP_LEVEL),
    }


def write_manifest(exported_records: list, path: str):
    manifest = build_manifest(exported_records)
    # unexpected_fields 가 있으면 그 자체로 위반 (정상 export 라면 빈 리스트여야 함)
    if manifest["unexpected_fields"]:
        raise ExportError(
            f"Manifest 생성 중 이상 탐지: unexpected_fields={manifest['unexpected_fields']}"
        )
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    return manifest


# ─────────────────────────────────────────────────────────────
# 셀프 테스트
# ─────────────────────────────────────────────────────────────
def _make_sample_ops_record():
    """Decision §18.1 운영 DB 스키마 예시 기반 테스트 레코드."""
    return {
        "session_id": "20260421-234412-a3f8b2e1",
        "patient_key": "abc123de",                # forbidden
        "patient_context": {                       # forbidden (컨테이너째)
            "patient_no": "C-00123",
            "age_years": 30,
            "age_major": "30대",
            "age_minor": "30대",
            "age_flags": [],
            "sex": "F",
        },
        "encounter_meta": {                        # forbidden
            "chart_date": "2026-04-21",
            "doctor_code": "D03",
            "captured_at": "2026-04-21T23:27:44",
        },
        "clinical_regions": {
            "symptoms": "rhinorrhea 3d",
            "special": "PCN allergy",
            "dx": "j00",
            "orders": "cefa 3T 3d",
        },
        "vitals_context": {
            "BT": 37.4, "BW": None, "BP1": None,
            "BP2": None, "PR": None, "BST": None,
        },
        "aux": {"statement_context": "MX999..."},  # forbidden
    }


def _make_dataset_ready_record():
    """이미 필드 분리된 상태 (진료실 PC ETL 거친 결과 시뮬레이션)."""
    return {
        "session_id": "20260421-234412-a3f8b2e1",
        "age_major": "30대",
        "age_minor": "30대",
        "age_flags": [],
        "sex": "F",
        "chart_date": "2026-04-21",
        "clinical_regions": {
            "symptoms": "rhinorrhea 3d", "special": "PCN allergy",
            "dx": "j00", "orders": "cefa 3T 3d",
        },
        "vitals_context": {
            "BT": 37.4, "BW": None, "BP1": None,
            "BP2": None, "PR": None, "BST": None,
        },
    }


def _selftest():
    import tempfile
    print("=" * 60)
    print("  export_dataset 셀프 테스트")
    print("=" * 60)

    # [1] 정상 레코드 export
    print("\n[1] 정상 (dataset-ready) 레코드")
    rec = _make_dataset_ready_record()
    out = export_record(rec)
    print(f"    필드: {sorted(out.keys())}")
    assert "session_id" in out
    assert "patient_key" not in out
    assert "age_years" not in out
    print("    ✓ allowlist 필드만 남음")

    # [2] 운영 DB 원본 (forbidden 필드 포함) → fail-fast
    print("\n[2] 운영 DB 원본 (forbidden 포함)")
    bad = _make_sample_ops_record()
    try:
        export_record(bad)
        raise AssertionError("forbidden 이 있는데 export 가 성공함")
    except ExportError as e:
        print(f"    ✓ ExportError 발생: {str(e)[:80]}...")

    # [2b] unknown top-level field (Patch A: 반드시 실패해야 함)
    print("\n[2b] Unknown top-level field (Patch A 신규)")
    rec2b = _make_dataset_ready_record()
    rec2b["name"] = "홍길동"  # allowlist 에도 없고 forbidden 에도 없음
    try:
        export_record(rec2b)
        raise AssertionError("unknown field 'name' 이 있는데 export 가 성공함 → Patch A 구멍")
    except ExportError as e:
        msg = str(e)
        assert "name" in msg, f"에러 메시지에 'name' 이 없음: {msg}"
        print(f"    ✓ ExportError 발생: {msg[:100]}...")

    # [2c] sanitize_operational_record_for_dataset (위험 함수) 는 조용히 필터링 OK
    print("\n[2c] sanitize_operational_record_for_dataset (위험 함수) 동작")
    sanitized = sanitize_operational_record_for_dataset(_make_sample_ops_record())
    assert "patient_key" not in sanitized
    assert "session_id" in sanitized
    print(f"    ✓ 조용한 필터링 완료. 필드: {sorted(sanitized.keys())}")
    # 그리고 이 결과는 export_record 에 다시 넣어도 통과
    re_exported = export_record(sanitized)
    print(f"    ✓ 결과를 export_record 에 재투입 성공 (이중 검증)")

    # [2d] Patch A+ nested smuggling (dict value 안에 PHI)
    print("\n[2d] Patch A+: nested smuggling - dict value 안에 patient_no")
    rec2d = _make_dataset_ready_record()
    rec2d["sex"] = {"patient_no": "C-00123", "value": "F"}  # sex 는 allowed 지만 내부 PHI
    try:
        export_record(rec2d)
        raise AssertionError("nested patient_no 가 통과함 → Patch A+ 구멍")
    except ExportError as e:
        msg = str(e)
        assert "patient_no" in msg
        assert "sex.patient_no" in msg or "sex" in msg
        print(f"    ✓ ExportError: {msg[:100]}...")

    # [2e] Patch A+ nested smuggling (list of dicts)
    print("\n[2e] Patch A+: nested smuggling - list 안의 dict 에 phone")
    rec2e = _make_dataset_ready_record()
    rec2e["age_flags"] = [{"phone": "010-1234-5678"}]
    try:
        export_record(rec2e)
        raise AssertionError("list 내부 phone 이 통과함 → Patch A+ 구멍")
    except ExportError as e:
        msg = str(e)
        assert "phone" in msg
        print(f"    ✓ ExportError: {msg[:100]}...")

    # [2f] Patch A+ any-depth: clinical_regions 안에 patient_name
    print("\n[2f] Patch A+: clinical_regions 안에 patient_name 숨김")
    rec2f = _make_dataset_ready_record()
    rec2f["clinical_regions"]["symptoms"] = {"text": "...", "patient_name": "홍길동"}
    # 이건 clinical_regions 서브키 검사 (Step 2, _build_clean_record) 에서도 막히고
    # any-depth 검사 (Step 3, _validate_allowlist) 에서도 막힘. 어느 쪽이든 실패면 OK.
    try:
        export_record(rec2f)
        raise AssertionError("clinical_regions 안의 patient_name 이 통과함")
    except ExportError as e:
        print(f"    ✓ ExportError: {str(e)[:100]}...")

    # [3] clinical_regions 에 허용되지 않은 서브키
    print("\n[3] clinical_regions 허용 외 서브키")
    rec3 = _make_dataset_ready_record()
    rec3["clinical_regions"]["patient_no"] = "X"  # 이상한 서브키 삽입 시도
    try:
        export_record(rec3)
        raise AssertionError("서브키 허용 외인데 성공함")
    except ExportError as e:
        print(f"    ✓ ExportError 발생: {str(e)[:80]}...")

    # [4] session_id 누락
    print("\n[4] session_id 누락")
    rec4 = _make_dataset_ready_record()
    del rec4["session_id"]
    try:
        export_record(rec4)
        raise AssertionError("session_id 없는데 성공함")
    except ExportError as e:
        print(f"    ✓ ExportError: {e}")

    # [5] 일괄 export
    print("\n[5] 일괄 export")
    batch = [_make_dataset_ready_record() for _ in range(3)]
    batch[1]["session_id"] = "20260421-234500-bbbbbbbb"
    batch[2]["session_id"] = "20260421-234600-cccccccc"
    exported = export_records(batch)
    assert len(exported) == 3
    print(f"    ✓ {len(exported)} 건 export 성공")

    # [6] manifest
    print("\n[6] manifest 생성")
    with tempfile.TemporaryDirectory() as td:
        m_path = os.path.join(td, "manifest.json")
        manifest = write_manifest(exported, m_path)
        with open(m_path, encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["record_count"] == 3
        assert loaded["unexpected_fields"] == []
        print(f"    ✓ manifest 기록됨. record_count={loaded['record_count']}")
        print(f"    ✓ fields_in_all_records = {loaded['fields_in_all_records']}")

    # [7] 일괄 export 중 하나라도 실패하면 전체 중단
    print("\n[7] 일괄 처리 중 실패 전파")
    mixed = [
        _make_dataset_ready_record(),
        _make_sample_ops_record(),  # forbidden 포함
        _make_dataset_ready_record(),
    ]
    try:
        export_records(mixed)
        raise AssertionError("forbidden 포함 레코드 있는데 전체 성공함")
    except ExportError as e:
        print(f"    ✓ 전체 실패 (index 지시): {str(e)[:100]}...")

    print("\n모든 테스트 통과.")


if __name__ == "__main__":
    _selftest()
