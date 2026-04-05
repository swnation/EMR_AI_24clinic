import json
from typing import List, Dict

with open("rules/rules.json", encoding="utf-8") as f:
    RULES = json.load(f)["rules"]

# ── 상병 코드 세트 ──
RESP_CODES = {"j00","j040","j060","j0180","j0390","j209","j189","j303","j22","j111"}
MUSCULO_CODES = {"m545","m542","m79","m791","m792"}
SKIN_ALLERGY_CODES = {"l309","l500","l501","l509"}

# ── 약품 코드 세트 ──

# 진해거담제
ANTITUSSIVE_ADULT = {"co","cosy","drop","erdo","ac"}
ANTITUSSIVE_PED = {"dropsy","umk","ac2"}

# drop + ac 병용 금기 조합
DROP_AC_CONFLICT = {"drop","ac"}
DROP_AC_CONFLICT_PED = {"dropsy","ac2"}

# IM 주사제 코드 (비급여-b 코드 존재하는 것들)
IM_CODES = {"tra","d","bus","tr","mac","pheni","dexa","genta","linco","ambi","epi"}

# 항생제 코드
ANTIBIOTICS = {"aug2","cefa","clari","cipro","levo","levo250","augsy","cefasy","3cefa","3cefaiv","ampiiv"}

# 수액 코드
IV_FLUID_CODES = {"ns","ns110","mc","gw6","gw8","gw10","gw15","3cefaiv","ampiiv"}

# 타미플루 계열
TAMIFLU_CODES = {"tami75","tami30","tami45","tamisy","tamiiv"}


def run_check(dx: List[str], orders: List[str], symptoms: str, patient_type: str) -> List[Dict]:
    dx_set = {c.lower().strip() for c in dx}
    order_set = {c.lower().strip() for c in orders}
    results = []

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # URI 핵심 룰 — 삭감/금기
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ① loxo + 호흡기 상병만 → 근골격계 상병 없음
    if "loxo" in order_set:
        has_resp = bool(dx_set & RESP_CODES)
        has_musculo = bool(dx_set & MUSCULO_CODES)
        if has_resp and not has_musculo:
            results.append({
                "level": "err",
                "message": "loxo + 호흡기 상병만 있음 → 삭감 대상",
                "sub": "m545(아래허리통증) 등 근골격계 상병 추가 필요",
                "source": "성인 URI.md"
            })

    # ② 성인 진해거담제 2종 초과
    if patient_type == "성인":
        used_antitussive = order_set & ANTITUSSIVE_ADULT
        if len(used_antitussive) > 2:
            results.append({
                "level": "err",
                "message": f"진해거담제 {len(used_antitussive)}종 → 성인은 2종까지만 보험",
                "sub": f"사용 중: {', '.join(sorted(used_antitussive))}",
                "source": "성인 URI.md"
            })

    # ③ 소아 진해거담제 초과 (6세미만 3종, 6세이상 2종)
    if patient_type == "소아":
        used_ped_antitussive = order_set & ANTITUSSIVE_PED
        if len(used_ped_antitussive) > 3:
            results.append({
                "level": "err",
                "message": f"소아 진해거담제 {len(used_ped_antitussive)}종 → 삭감",
                "sub": "6세미만 최대 3종, 6세이상 최대 2종까지 보험",
                "source": "소아 URI(만12세 미만).md"
            })

    # ④ drop + ac 병용 삭감 (성인)
    if patient_type == "성인" and DROP_AC_CONFLICT.issubset(order_set):
        results.append({
            "level": "err",
            "message": "drop + ac 병용 → 삭감 대상",
            "sub": "같은 작용(거담) 약물 중복. 하나만 선택",
            "source": "성인 URI.md"
        })

    # ⑤ dropsy + ac2 병용 삭감 (소아)
    if patient_type == "소아" and DROP_AC_CONFLICT_PED.issubset(order_set):
        results.append({
            "level": "err",
            "message": "dropsy + ac2 병용 → 삭감 대상",
            "sub": "같은 작용(거담) 약물 중복. 하나만 선택",
            "source": "소아 URI(만12세 미만).md"
        })

    # ⑥ umk 소아 용량 고정 경고
    if patient_type == "소아" and "umk" in order_set:
        results.append({
            "level": "warn",
            "message": "umk(움카민) 소아 용량 고정 — 벗어나면 삭감",
            "sub": "1~6세미만: 9mL TID / 6~12세미만: 18mL TID",
            "source": "소아 URI(만12세 미만).md"
        })

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 주사/수액 룰
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ⑦ 주사 2종 이상 → -b 코드
    used_im = order_set & IM_CODES
    if len(used_im) >= 2:
        results.append({
            "level": "warn",
            "message": f"주사제 {len(used_im)}종 → 추가분은 비급여(-b) 코드 사용",
            "sub": f"사용 중: {', '.join(sorted(used_im))} | ex) genta→gentab, dexa→dexab (디클로페낙 제외)",
            "source": "인수인계_2026년3월.md"
        })

    # ⑧ 소아 수액(IV) 금지 (12세 미만)
    if patient_type == "소아" and (order_set & IV_FLUID_CODES):
        used_iv = order_set & IV_FLUID_CODES
        results.append({
            "level": "err",
            "message": "소아(12세 미만) IV 수액 불가",
            "sub": f"수액코드 감지: {', '.join(sorted(used_iv))}. 12세 미만은 수액 처방 안 됨",
            "source": "소아 URI(만12세 미만).md"
        })

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 독감/항바이러스 룰
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ⑨ 타미플루 + 독감 상병 누락
    used_tami = order_set & TAMIFLU_CODES
    if used_tami:
        has_flu = _dx_startswith(dx_set, "j09") or _dx_startswith(dx_set, "j10") or _dx_startswith(dx_set, "j11")
        if not has_flu:
            results.append({
                "level": "warn",
                "message": "타미플루 처방 → 독감(J09~J11) 상병 확인",
                "sub": "독감 상병 없이 타미플루 처방 시 보험 문제",
                "source": "독감 influenza.md"
            })

    # ⑩ 타미플루 예방목적(QD x10일) → 비보험 안내
    # (코드만으로 예방/치료 구분 어려움 → 안내 수준)
    if used_tami and not (_dx_startswith(dx_set, "j09") or _dx_startswith(dx_set, "j10") or _dx_startswith(dx_set, "j11")):
        results.append({
            "level": "info",
            "message": "타미플루 예방목적(QD x10일)은 비보험",
            "sub": "치료: 75mg BID x5d / 예방: 75mg QD x10d(비보험)",
            "source": "독감 influenza.md"
        })

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 일반 룰 — 상병/오더 공통
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ⑪ dige 코드 사용 금지 (ranitidine → 시장 철수)
    if any(c in order_set for c in ["dige","ranitidine"]):
        results.append({
            "level": "err",
            "message": "dige(ranitidine) 사용 불가 — 시장 철수 성분",
            "sub": "대체: reba(무코란) 또는 ppiiv(판타졸주사)",
            "source": "인수인계_2026년3월.md"
        })

    # ⑫ 글리아티린 60세 미만 경고
    if "glia8" in order_set:
        results.append({
            "level": "warn",
            "message": "글리아티린(glia8): 60세 미만 금기 — 나이 확인 필수",
            "sub": "반드시 전화로 확인 후 처방",
            "source": "인수인계_2026년3월.md"
        })

    # ⑬ cd 상병 순서
    if "cd" in order_set:
        results.append({
            "level": "warn",
            "message": "cd(만성질환관리료) 관련 상병이 주상병 최상위에 있어야 함",
            "sub": "고혈압/당뇨 등 만성질환 상병을 상병 목록 맨 위로",
            "source": "인수인계_2026년3월.md"
        })

    # ⑭ 배제 상병(Z코드)이 주상병
    if dx and len(dx) > 0:
        first_dx = dx[0].lower().strip()
        if first_dx.startswith("z") and len(dx_set) > 1:
            results.append({
                "level": "warn",
                "message": f"주상병이 배제코드({first_dx}) → 주상병으로 부적절",
                "sub": "배제된 상병(Z코드)은 주상병 위치에 올 수 없음. 순서 변경 필요",
                "source": "인수인계_2026년3월.md"
            })

    # ⑮ 항생제 + 호흡기 상병 확인 (상병 누락 방지)
    used_ab = order_set & ANTIBIOTICS
    if used_ab and not dx_set:
        results.append({
            "level": "warn",
            "message": "항생제 처방 있는데 상병코드 없음",
            "sub": f"항생제: {', '.join(sorted(used_ab))}. 적응증에 맞는 상병 추가 필요",
            "source": "항생제 정리.md"
        })

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 결과 없으면 OK
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if not results:
        results.append({
            "level": "ok",
            "message": "체크 항목 이상 없음",
            "sub": "",
            "source": ""
        })

    return results


def _dx_startswith(dx_set: set, prefix: str) -> bool:
    """상병코드 세트에서 특정 접두사로 시작하는 코드가 있는지"""
    return any(c.startswith(prefix) for c in dx_set)
