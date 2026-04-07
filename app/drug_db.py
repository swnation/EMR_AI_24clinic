"""
약물 DB — data/drugs/*.json 로드 + 코드별 조회
checker.py에서 하드코딩된 상수 대신 이 모듈을 사용
"""
import json
import os
from typing import Dict, List, Optional, Set

_BASE = os.path.join(os.path.dirname(__file__), "..", "data", "drugs")
_FILES = [
    "respiratory.json",
    "pain.json",
    "gi.json",
    "antibiotics.json",
    "injection.json",
    "chronic_etc.json",
]

# ── 전체 약물 flat dict: code → info ──
_drugs: Dict[str, dict] = {}
# ── 카테고리별 코드 세트 ──
_category_codes: Dict[str, Set[str]] = {}
# ── 원본 JSON (메타데이터 규칙 접근용) ──
_raw: Dict[str, dict] = {}


def _is_drug_entry(v: dict) -> bool:
    """name 키가 있고 str이면 약물 엔트리로 간주"""
    return isinstance(v, dict) and isinstance(v.get("name"), str)


def _walk(obj, category: str, file_key: str):
    """JSON 트리를 순회하며 약물 엔트리를 _drugs에 등록"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.startswith("_"):
                continue
            if _is_drug_entry(v):
                v["_code"] = k
                v["_category"] = category
                v["_file"] = file_key
                _drugs[k] = v
                _category_codes.setdefault(category, set()).add(k)
            elif isinstance(v, dict):
                # 서브카테고리
                sub_cat = category + "/" + k if not k.startswith("_") else category
                _walk(v, sub_cat, file_key)


def load():
    """data/drugs/*.json 전부 로드"""
    _drugs.clear()
    _category_codes.clear()
    _raw.clear()
    for fname in _FILES:
        path = os.path.join(_BASE, fname)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        file_key = fname.replace(".json", "")
        _raw[file_key] = data
        for section_name, section_val in data.items():
            if section_name.startswith("_"):
                continue
            _walk(section_val, section_name, file_key)


# ── 초기 로드 ──
load()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 조회 API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get(code: str) -> Optional[dict]:
    """코드로 약물 정보 조회. 없으면 None"""
    return _drugs.get(code)


def get_all() -> Dict[str, dict]:
    """전체 약물 dict 반환"""
    return dict(_drugs)


def codes_in(category_substring: str) -> Set[str]:
    """카테고리명에 substring이 포함된 모든 약물 코드"""
    result = set()
    for cat, codes in _category_codes.items():
        if category_substring in cat:
            result |= codes
    return result


def codes_with_field(field: str, value=None) -> Set[str]:
    """특정 필드가 있는 (또는 특정 값인) 약물 코드"""
    result = set()
    for code, info in _drugs.items():
        if field in info:
            if value is None or info[field] == value:
                result.add(code)
    return result


def raw(file_key: str) -> dict:
    """원본 JSON 접근 (메타데이터 규칙 등)"""
    return _raw.get(file_key, {})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# checker.py에서 쓸 편의 세트들 (하드코딩 대체)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def nsaid_codes() -> Set[str]:
    return codes_in("NSAIDs")

def aap_codes() -> Set[str]:
    return codes_in("AAP") - codes_in("AAP_주사")

def antibiotics_codes() -> Set[str]:
    """항생제 코드 (항바이러스/항진균 제외)"""
    result = set()
    for cat in ["페니실린계", "세팔로스포린계", "마크로라이드계", "퀴놀론계", "기타_항생제"]:
        result |= codes_in(cat)
    return result

def antitussive_adult_codes() -> Set[str]:
    """성인 진해거담제 카운팅 대상"""
    resp = raw("respiratory")
    rules = resp.get("_antitussive_count_rules", {})
    adult = rules.get("성인", {}).get("상기도", {})
    return set(adult.get("counted", []))

def antitussive_ped_codes() -> Set[str]:
    """소아 진해거담제 카운팅 대상"""
    resp = raw("respiratory")
    rules = resp.get("_antitussive_count_rules", {})
    codes = set()
    for key in ["소아_6세미만", "소아_6세이상"]:
        sub = rules.get(key, {})
        codes |= set(sub.get("counted", []))
    return codes

def im_codes() -> Set[str]:
    """IM 주사제 코드 (base만, -b 제외)"""
    result = set()
    for cat in ["IM_진통소염", "IM_항히스타민_스테로이드", "IM_항생제", "IM_기타"]:
        for code in codes_in(cat):
            info = get(code)
            if info and not info.get("is_b_code"):
                result.add(code)
    return result

def iv_fluid_codes() -> Set[str]:
    return codes_in("IV_수액_기본") | codes_in("IV_영양수액")

def tamiflu_codes() -> Set[str]:
    return codes_in("항바이러스제_인플루엔자")

def prokinetics_codes() -> Set[str]:
    return codes_in("위장관운동촉진제")

def b_code_pairs() -> List[dict]:
    """IM -b 코드 페어 목록"""
    inj = raw("injection")
    pairs_data = inj.get("_im_b_code_pairs", {})
    return pairs_data.get("pairs", [])

def same_class_conflicts() -> List[dict]:
    """같은 분류 병용 금기 목록"""
    resp = raw("respiratory")
    return resp.get("_same_class_conflicts", [])

# ── 동일 성분 그룹 ──
_generic_groups: Dict[str, List[str]] = {}
_code_to_generic: Dict[str, str] = {}

def _load_generic_groups():
    path = os.path.join(_BASE, "generic_groups.json")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for generic_name, info in data.items():
        if generic_name.startswith("_"):
            continue
        codes = info.get("codes", [])
        _generic_groups[generic_name] = codes
        for c in codes:
            _code_to_generic[c] = generic_name

_load_generic_groups()


def same_generic(code: str) -> Set[str]:
    """같은 성분의 다른 코드들 반환 (자기 자신 포함)"""
    generic = _code_to_generic.get(code)
    if not generic:
        return {code}
    return set(_generic_groups.get(generic, [code]))


def generic_name(code: str) -> Optional[str]:
    """코드의 성분 그룹명 반환"""
    return _code_to_generic.get(code)


def all_generic_groups() -> Dict[str, List[str]]:
    """전체 성분 그룹 반환"""
    return dict(_generic_groups)


def drug_conflicts(file_key: str) -> List[dict]:
    """파일별 _conflicts 목록"""
    data = raw(file_key)
    return data.get("_conflicts", [])
