import json
from typing import List, Dict

with open("rules/rules.json", encoding="utf-8") as f:
    RULES = json.load(f)["rules"]

# ── 상병 코드 세트 ──
RESP_CODES = {"j00","j040","j060","j0180","j0390","j209","j189","j303","j22","j111"}
MUSCULO_CODES = {"m545","m542","m79","m791","m792"}

# 만성질환 상병 (cd 청구 대상)
CHRONIC_DX = {
    "i10","i109","i110","i119",                   # 고혈압
    "e10","e11","e14","e110","e119","e149",        # 당뇨
}
# 이상지질혈증 (cd 비대상)
DYSLIPIDEMIA_DX = {"e780","e781","e782","e785","e78"}

# 심부전 상병
HEART_FAILURE_DX = {"i500","i501","i509","i50"}

# clopidogrel 필요 상병
CLOPIDOGREL_DX = {"i252","i638","i639","i63","i251","i259","i70","i74"}

# ── 약품 코드 세트 ──
ANTITUSSIVE_ADULT = {"co","cosy","drop","erdo","ac"}
ANTITUSSIVE_PED = {"dropsy","umk","ac2"}

# IM 주사제 코드 (비급여-b 코드 존재하는 것들)
IM_CODES = {"tra","d","bus","tr","mac","pheni","dexa","genta","linco","ambi","epi"}

# 편두통 급성기 진통제
MIGRAINE_ANALGESICS = {"loxo","dexi","ty","semi"}

# 당뇨 환자 금기약
DM_CONTRAINDICATED = {"pseudo","pseudoephedrine","슈도에페드린"}

# 항혈소판제
ANTIPLATELET_CODES = {"clopi","clopidogrel","플라빅스","aspirin","asp","sarpo","cilostazol"}


def _dx_startswith(dx_set: set, prefix: str) -> bool:
    """상병코드 세트에서 특정 접두사로 시작하는 코드가 있는지"""
    return any(c.startswith(prefix) for c in dx_set)


def run_check(dx: List[str], orders: List[str], symptoms: str, patient_type: str) -> List[Dict]:
    dx_set = {c.lower().strip() for c in dx}
    order_set = {c.lower().strip() for c in orders}
    results = []

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 기존 룰 ①~⑩
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ① loxo + 호흡기 상병 → 근골격계 상병 없음
    if "loxo" in order_set:
        has_resp = bool(dx_set & RESP_CODES)
        has_musculo = bool(dx_set & MUSCULO_CODES)
        if has_resp and not has_musculo:
            results.append({
                "level": "err",
                "message": "loxo + 호흡기 상병만 있음 → 삭감 대상",
                "sub": "m545(아래허리통증) 등 근골격계 상병 추가 필요",
                "source": "인수인계_2026년3월.docx"
            })

    # ② cipro 방광염 1차 → n12-3 필요
    if "cipro" in order_set and "n300" in dx_set:
        if not ({"n12-3","n12-2"} & dx_set):
            results.append({
                "level": "err",
                "message": "cipro 방광염 1차 처방 시 n12-3 신우신염 NOS 상병 추가 필요",
                "sub": "방광염 n300 단독으로 cipro 1차 처방은 보험 문제",
                "source": "급성 방광염 acute cystitis.md"
            })

    # ③ levofloxacin 고용량
    if any(c in order_set for c in ["levo500","크라비트500"]):
        results.append({
            "level": "err",
            "message": "levofloxacin 500~750mg QD → 삭감 대상",
            "sub": "250mg QD x10d 사용",
            "source": "신우신염 APN acute pyelonephritis.md"
        })

    # ④ 신우신염 + 디클로페낙 → 기타근통 코드
    if "d" in order_set and ({"n12-3","n12-2"} & dx_set):
        results.append({
            "level": "warn",
            "message": "신우신염 + 디클로페낙: 자동입력 기타근통 코드 삭제 필요",
            "sub": "연결코드 m79108 기타근통 삭제",
            "source": "신우신염 APN acute pyelonephritis.md"
        })

    # ⑤ 모누롤산
    if any(c in order_set for c in ["mono","fosfomycin","모누롤산"]):
        results.append({
            "level": "warn",
            "message": "모누롤산: 반드시 1,1,1로 처방",
            "sub": "딱 한 번 복용. 단순 UTI 아닌 경우 금기",
            "source": "급성 방광염 acute cystitis.md"
        })

    # ⑥ 소아 quinolone
    if patient_type == "소아" and ({"cipro","levo","levo250","levo500"} & order_set):
        results.append({
            "level": "err",
            "message": "소아 quinolone(cipro/levofloxacin) 금기",
            "sub": "1차: augsy 또는 cefasy",
            "source": "소아 UTI.md"
        })

    # ⑦ 진해거담제 성인 2종 초과
    if patient_type == "성인":
        used_antitussive = order_set & ANTITUSSIVE_ADULT
        if len(used_antitussive) > 2:
            results.append({
                "level": "err",
                "message": f"진해거담제 {len(used_antitussive)}종 → 성인은 2종까지만 보험",
                "sub": f"사용 중: {', '.join(sorted(used_antitussive))}",
                "source": "성인 URI.md"
            })

    # ⑧ umk 소아 용량 경고
    if patient_type == "소아" and "umk" in order_set:
        results.append({
            "level": "warn",
            "message": "umk(움카민) 소아 용량 고정 — 벗어나면 삭감",
            "sub": "1~6세미만: 9mL TID / 6~12세미만: 18mL TID",
            "source": "소아 URI(만12세 미만).md"
        })

    # ⑨ 글리아티린 60세 미만 경고
    if "glia8" in order_set:
        results.append({
            "level": "warn",
            "message": "글리아티린(glia8): 60세 미만 금기 — 나이 확인 필수",
            "sub": "반드시 전화로 확인 후 처방",
            "source": "인수인계_2026년3월.docx"
        })

    # ⑩ 주사 2종 이상
    used_im = order_set & IM_CODES
    if len(used_im) >= 2:
        results.append({
            "level": "warn",
            "message": f"주사제 {len(used_im)}종 → 추가분은 비급여(-b) 코드 사용",
            "sub": f"사용 중: {', '.join(sorted(used_im))} | ex) genta→gentab",
            "source": "인수인계_2026년3월.docx"
        })

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 추가 룰 ⑪~⑱
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ⑪ dige 코드 사용 금지 (ranitidine 성분 → 시장 철수)
    if any(c in order_set for c in ["dige","ranitidine","란소프라졸"]):
        results.append({
            "level": "err",
            "message": "dige(ranitidine) 사용 불가 — 시장 철수 성분",
            "sub": "대체: reba(무코란) 또는 ppiiv(판타졸주사)",
            "source": "인수인계_2026년3월.docx"
        })

    # ⑫ clopidogrel 단독 → 필요 상병 누락
    if any(c in order_set for c in ["clopi","clopidogrel","플라빅스"]):
        has_required = bool(dx_set & CLOPIDOGREL_DX)
        if not has_required:
            results.append({
                "level": "err",
                "message": "clopidogrel(플라빅스) → 필수 상병 누락",
                "sub": "i252(만성허혈성심질환) 또는 i638(기타뇌경색) 등 추가 필요",
                "source": "항혈소판제.md"
            })

    # ⑬ 이상지질혈증 + cd 오더 → cd 비대상
    if "cd" in order_set:
        has_dyslipidemia = bool(dx_set & DYSLIPIDEMIA_DX) or _dx_startswith(dx_set, "e78")
        has_chronic = bool(dx_set & CHRONIC_DX)
        if has_dyslipidemia and not has_chronic:
            results.append({
                "level": "err",
                "message": "이상지질혈증 단독 → 만성질환관리료(cd) 청구 불가",
                "sub": "고혈압/당뇨 상병이 함께 있어야 cd 청구 가능",
                "source": "고지혈증 이상지질혈증 dyslipidemia.md"
            })

    # ⑭ bisoprolol 2.5mg → 심부전 상병 필요
    if any(c in order_set for c in ["bisoprolol","비소프롤롤","콩코르2.5"]):
        has_hf = bool(dx_set & HEART_FAILURE_DX) or _dx_startswith(dx_set, "i50")
        if not has_hf:
            results.append({
                "level": "warn",
                "message": "bisoprolol 2.5mg → 심부전(I50) 상병 추가 확인",
                "sub": "심부전 상병 없이 2.5mg은 보험 문제 가능",
                "source": "고혈압 HTN hypertension.md"
            })

    # ⑮ 편두통: 크래밍 + 진통제 중복
    if any(c in order_set for c in ["크래밍","cramming","ergot"]):
        overlap = order_set & MIGRAINE_ANALGESICS
        if len(overlap) > 1:
            results.append({
                "level": "err",
                "message": f"편두통 급성기 진통제 {len(overlap)+1}종 → 삭감 대상",
                "sub": f"크래밍 + NSAIDs/ty/semi 중 1가지만 가능. 사용 중: 크래밍, {', '.join(sorted(overlap))}",
                "source": "편두통 migraine.md"
            })
        elif len(overlap) == 1:
            pass  # 크래밍 + 1종은 OK
        # 크래밍 단독도 OK

    # ⑯ 당뇨 환자 + pseudoephedrine 금기
    has_dm = bool(dx_set & CHRONIC_DX & {"e10","e11","e14","e110","e119","e149"})
    if has_dm and (order_set & DM_CONTRAINDICATED):
        results.append({
            "level": "err",
            "message": "당뇨 환자에 pseudoephedrine 절대 금기",
            "sub": "혈당 상승 + 혈압 상승 위험. 대체제 사용",
            "source": "당뇨 DM diabetes.md"
        })

    # ⑰ 항혈소판제 2종 이상 동시 처방
    used_antiplatelet = order_set & ANTIPLATELET_CODES
    if len(used_antiplatelet) >= 2:
        results.append({
            "level": "warn",
            "message": f"항혈소판제 {len(used_antiplatelet)}종 동시 처방 → 삭감 주의",
            "sub": f"사용 중: {', '.join(sorted(used_antiplatelet))}. 보험 인정 조건 확인 필요",
            "source": "항혈소판제.md"
        })

    # ⑱ 배제된 상병(Z코드 등)이 주상병(첫번째)에 있는 경우
    if dx and len(dx) > 0:
        first_dx = dx[0].lower().strip()
        if first_dx.startswith("z") and len(dx_set) > 1:
            results.append({
                "level": "warn",
                "message": f"주상병이 배제코드({first_dx}) → 주상병으로 부적절",
                "sub": "배제된 상병(Z코드)은 주상병 위치에 올 수 없음. 순서 변경 필요",
                "source": "인수인계_2026년3월.docx"
            })

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 결과 없으면 OK
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if not results:
        results.append({
            "level": "ok",
            "message": "체크 항목 이상 없음",
            "sub": "",
            "source": ""
        })

    return results
