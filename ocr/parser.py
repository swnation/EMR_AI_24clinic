"""
OCR 텍스트 → 상병코드/오더코드 파싱 + fuzzy 보정
"""
import json
import os
import re
from typing import List, Dict, Optional, Tuple

try:
    from rapidfuzz import fuzz, process
except ImportError:
    fuzz = None
    process = None

# 약품 코드 DB 로드 (처방자료-모두.xls에서 추출한 코드↔명칭)
_drug_names: Dict[str, str] = {}  # code → name
_drug_codes_set: set = set()


def _load_drug_db():
    """drug_db에서 코드 목록 로드"""
    global _drug_names, _drug_codes_set
    try:
        from app import drug_db
        for code, info in drug_db.get_all().items():
            _drug_names[code] = info.get("name", "")
            _drug_codes_set.add(code)
    except Exception:
        pass


_load_drug_db()

# ── 상병코드 패턴 ──
# ICD-10 형식: 알파벳 + 숫자 (j00, j0390, k297, m545, e14 등)
DX_PATTERN = re.compile(r'\b([a-zA-Z]\d{2,5}(?:-\d{1,2})?)\b')

# ── 오더코드 패턴 ──
# 영문 소문자 시작, 숫자 포함 가능 (aug2, loxo, ty325, 3cefa 등)
ORDER_PATTERN = re.compile(r'\b([a-z][a-z0-9+]*\d*)\b', re.IGNORECASE)


def parse_dx(text: str) -> List[str]:
    """상병 영역 텍스트에서 상병코드 추출"""
    if not text:
        return []
    # 소문자 변환 후 매칭
    codes = DX_PATTERN.findall(text.lower())
    # 중복 제거, 순서 유지
    seen = set()
    result = []
    for c in codes:
        c = c.strip()
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result


def parse_orders(text: str) -> List[Dict]:
    """
    오더 영역 텍스트에서 오더코드 + 용량/일수 추출
    반환: [{"code": "aug2", "dose": 3.0, "days": 3, "freq": 3}, ...]
    """
    if not text:
        return []

    lines = text.strip().split('\n')
    result = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 코드 추출 (첫 번째 영문 토큰)
        tokens = line.split()
        code = None
        for t in tokens:
            t_lower = t.lower().strip()
            # drug_db에 있는 코드인지 확인
            if t_lower in _drug_codes_set:
                code = t_lower
                break
            # fuzzy 매칭 (score 85+)
            if fuzz and process and len(t_lower) >= 2:
                match = process.extractOne(
                    t_lower, list(_drug_codes_set),
                    scorer=fuzz.ratio, score_cutoff=85
                )
                if match:
                    code = match[0]
                    break

        if not code:
            continue

        # 코드와 약품명 이후의 숫자만 용량으로 사용
        # 코드 위치 이후 텍스트에서 한글 약품명을 건너뛴 뒤 숫자 추출
        code_idx = line.lower().find(code)
        after_code = line[code_idx + len(code):] if code_idx >= 0 else line

        # 한글 약품명 부분 건너뛰기 (한글+숫자+mg/ml 등 포함)
        after_name = re.sub(r'^[^\d]*(?:[\d]+(?:\.\d+)?(?:mg|ml|g|%|mcg)\S*\s*)', '', after_code, flags=re.IGNORECASE)
        if not after_name.strip():
            after_name = after_code

        # 남은 부분에서 숫자 추출 (용량 일수 횟수)
        numbers = re.findall(r'(\d+\.?\d*)', after_name)
        # 첫 번째 숫자가 약품명의 mg 숫자일 수 있으므로 필터링
        # 순수 용량/일수/횟수 패턴: 보통 1~10 범위
        clean_numbers = []
        for n in numbers:
            val = float(n)
            if val <= 100:  # 100 이하만 용량/일수/횟수로 간주
                clean_numbers.append(val)

        dose = clean_numbers[0] if len(clean_numbers) > 0 else None
        days = int(clean_numbers[1]) if len(clean_numbers) > 1 else None
        freq = int(clean_numbers[2]) if len(clean_numbers) > 2 else None

        result.append({
            "code": code,
            "dose": dose,
            "days": days,
            "freq": freq,
        })

    return result


def parse_symptoms(text: str) -> str:
    """증상 탭 텍스트 → 정리된 문자열"""
    if not text:
        return ""
    # 줄바꿈 정리
    return text.strip()


def parse_patient_type(text: str) -> str:
    """특이증상 탭에서 환자 유형 추정"""
    if not text:
        return "성인"
    lower = text.lower()
    # 소아 키워드
    if any(kw in lower for kw in ["소아", "pediatric", "ped", "아이", "개월", "세"]):
        return "소아"
    return "성인"


def parse_all(ocr_texts: dict) -> dict:
    """
    4개 영역 OCR 텍스트 → checker 입력 형태로 변환
    ocr_texts: {"symptoms": ..., "special": ..., "dx": ..., "orders": ...}
    반환: {"dx": [...], "orders": [...], "order_details": [...],
           "symptoms": "...", "patient_type": "성인|소아"}
    """
    dx = parse_dx(ocr_texts.get("dx", ""))
    order_details = parse_orders(ocr_texts.get("orders", ""))
    order_codes = [o["code"] for o in order_details]
    symptoms = parse_symptoms(ocr_texts.get("symptoms", ""))
    patient_type = parse_patient_type(ocr_texts.get("special", ""))

    return {
        "dx": dx,
        "orders": order_codes,
        "order_details": order_details,
        "symptoms": symptoms,
        "patient_type": patient_type,
    }


if __name__ == "__main__":
    # 테스트
    test_dx = "j0390 상세불명의 급성편도염\nk297 상세불명의 위염\nm545 아래허리통증"
    test_orders = """aug2 아목클정625mg 3 3 3
loxo 록소프로펜정 3 3 3
co 코데날정 4.5 3 3
erdo 에스텐캡슐 3 3 3
reba 무코란정 3 3 3"""

    print("=== 상병 파싱 ===")
    print(parse_dx(test_dx))
    print()
    print("=== 오더 파싱 ===")
    for o in parse_orders(test_orders):
        print(f"  {o}")
    print()
    print("=== 전체 파싱 ===")
    result = parse_all({"dx": test_dx, "orders": test_orders})
    print(json.dumps(result, indent=2, ensure_ascii=False))
