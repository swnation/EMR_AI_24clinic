import json
from typing import List, Dict

with open("rules/rules.json", encoding="utf-8") as f:
    RULES = json.load(f)["rules"]

# ── 상병 코드 세트 ──
RESP_CODES = {"j00","j040","j060","j0180","j0390","j209","j189","j303","j22","j111"}
MUSCULO_CODES = {"m545","m542","m79","m791","m792"}

# ── 진해거담제 (심평원 분류 기준) ──
# suda/suda2는 카운팅에서 제외됨
# 성인: co/cosy = cough, erdo/ac/drop = sputum → 총 2종까지
ANTITUSSIVE_ADULT = {"co","cosy","drop","erdo","ac"}
# 소아: dropsy/ambsy/umk = cough, ac2 = sputum → 6세미만 3종, 6세이상 2종
ANTITUSSIVE_PED = {"dropsy","ambsy","umk","ac2"}

# 같은 분류(sputum) 병용 삭감 조합
SPUTUM_ADULT = {"erdo","ac","drop"}    # 성인 sputum 분류
SPUTUM_PED = {"ac2"}                    # 소아 sputum 분류 (1종뿐이라 중복 없음)

# ── 약품별 필수 상병 ──
# ac/erdo → j040(후두염), j0180(부비동염), j209(기관지염) 중 하나 필요
AC_REQUIRED_DX = {"j040","j0180","j209"}
# umk → j209(기관지염) 필요
UMK_REQUIRED_DX = {"j209"}
# atock/pat → j209(기관지염) 또는 j459(천식) 필요
ATOCK_REQUIRED_DX = {"j209","j459"}
# tan(탄툼가글) → 하기도(j22,j209)에 삭감, 상기도만 가능
TAN_BANNED_DX = {"j22","j209"}

# ── IM 주사제 ──
IM_CODES = {"tra","d","bus","tr","mac","pheni","dexa","genta","linco","ambi","epi"}
# dexa 필수 상병: j040(후두염) 또는 j303(비염)
DEXA_REQUIRED_DX = {"j040","j303"}

# ── 수액 코드 ──
IV_FLUID_CODES = {"ns","ns110","mc","gw6","gw8","gw10","gw15","3cefaiv","ampiiv","tamiiv","tyiv"}

# ── 타미플루 계열 ──
TAMIFLU_CODES = {"tami75","tami30","tami45","tamisy","tamiiv"}
FLU_DX = {"j111","j111-1","j09","j10","j11"}

# ── 항생제 ──
ANTIBIOTICS = {"aug2","aug","cefa","clari","clari2","cipro","levo","levo250",
               "augsy","clarisy","cefasy","3cefa","3cefasy","3cefaiv","ampiiv","linco"}

# ── 약+약 삭감 (동시 보험 불가, 하나는 f12) ──
# co+cosy 같은 성분
# atock+pat 같은 분류
# ty+semi / NSAID+set / ty+set
NSAID_CODES = {"loxo","dexi","dexisy","bru","d"}
AAP_CODES = {"ty","ty325","tykid","semi","set"}

# 소화제 (2종 이상 삭감)
PROKINETICS = {"macpo","dom","trime","levo","mosa","trimesy"}

# ── 상병+약 삭감 (해당 상병으로는 보험 불가 → 추가 상병 필요) ──
# dexa/pd + 감기(j00)/인후두염(j060)/편도염(j0390)/기관지염(j209) → 삭감
# → 후두염(j040)/비염(j303)/피부염(l309)에만 보험
DEXA_PD_BANNED_DX = {"j00","j060","j0390","j209"}
DEXA_PD_OK_DX = {"j040","j303","l309","l500"}

# 비염(j303)에 항생제/NSAID 삭감
RHINITIS_DX = {"j303"}

# kina는 J코드(호흡기) 아니면 삭감
KINA_REQUIRED_PREFIX = "j"

# 바이럴 상병 (항생제 삭감)
VIRAL_DX = {"j111","j111-1","b084","b08","b01","b019"}  # 인플루엔자, 수족구, 수두

# 위염 상병
GASTRITIS_DX = {"k297","k29","k290","k295","k296"}
# 장염 상병
ENTERITIS_DX = {"a09","a090","a099","k529"}
# 식도염 상병
ESOPHAGITIS_DX = {"k210","k219","k21"}

# 두통 상병
HEADACHE_DX = {"r51"}

# 소화성궤양용제 (방어인자+공격인자 중 1종만)
GASTRIC_DEFENSE = {"reba"}              # 방어인자 증강
GASTRIC_ATTACK = {"cime","famo","ppi","ppi2","pcab"}  # 공격인자 억제 (H2 blocker + PPI)

# macpo/dom 필수 상병: r11(구역/구토)만
MACPO_DOM_REQUIRED_DX = {"r11"}
# levo/mosa: r11, k30, k58 가능
LEVO_MOSA_OK_DX = {"r11","k30","k58","k580","k581","k582","k589"}
# trime: 위염/장염/IBS/소화불량/구역 다 가능
TRIME_OK_DX = {"r11","k30","k58","k580","k581","k589","k297","k29","a090","a084","a049"}

# 대상포진
ZOSTER_DX = {"b029","b02"}
# 대상포진 후 신경통
ZOSTER_NEURALGIA_DX = {"g530"}

# 두드러기 상병
URTICARIA_DX = {"l500","l501","l509","l50"}

# epe(에페리손) 가능 상병: 경추통/요통만
EPE_OK_DX = {"m542","m545","m543","m544"}

# sme 필요: 설사 동반 장염
SME_OK_DX = {"a090","a084","a049","k581"}
SME_BANNED_DX = {"k589"}  # 설사 미동반 IBS

# tra 사용 불가 상병 (단독)
TRA_BANNED_DX = {"a090","a084","a049","k58","k30","r11","k297","k29","k296"}


def _dx_startswith(dx_set: set, prefix: str) -> bool:
    return any(c.startswith(prefix) for c in dx_set)


def _has_flu_dx(dx_set: set) -> bool:
    if dx_set & FLU_DX:
        return True
    return _dx_startswith(dx_set, "j09") or _dx_startswith(dx_set, "j10") or _dx_startswith(dx_set, "j11")


def run_check(dx: List[str], orders: List[str], symptoms: str, patient_type: str) -> List[Dict]:
    dx_set = {c.lower().strip() for c in dx}
    order_set = {c.lower().strip() for c in orders}
    results = []

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # [A] 진해거담제 룰
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # A-1. 성인 진해거담제 2종 초과
    if patient_type != "소아":
        used = order_set & ANTITUSSIVE_ADULT
        if len(used) > 2:
            results.append({
                "level": "err",
                "message": f"진해거담제 {len(used)}종 → 성인 2종까지만 보험",
                "sub": f"사용 중: {', '.join(sorted(used))}. suda는 카운팅 제외",
                "source": "인수인계_2026년3월.md"
            })

    # A-2. 성인 같은 분류(sputum) 약물 중복 → 삭감
    if patient_type != "소아":
        used_sputum = order_set & SPUTUM_ADULT
        if len(used_sputum) >= 2:
            results.append({
                "level": "err",
                "message": f"거담제(sputum) 중복: {', '.join(sorted(used_sputum))} → 삭감",
                "sub": "같은 분류(erdo/ac/drop) 병용 불가. 하나는 f12 비급여 처리",
                "source": "인수인계_2026년3월.md"
            })

    # A-3. 소아 진해거담제 초과 (6세미만 3종, 6세이상 2종)
    if patient_type == "소아":
        used = order_set & ANTITUSSIVE_PED
        # 정확한 나이를 모르므로 3종 초과시 경고
        if len(used) > 3:
            results.append({
                "level": "err",
                "message": f"소아 진해거담제 {len(used)}종 → 삭감",
                "sub": "6세미만 3종, 6세이상 2종까지. suda2는 카운팅 제외",
                "source": "소아 URI(만12세 미만).md"
            })

    # A-4. ac/erdo 처방 시 필수 상병(j040/j0180/j209) 누락
    if {"ac","erdo"} & order_set:
        if dx_set and not (dx_set & AC_REQUIRED_DX):
            results.append({
                "level": "warn",
                "message": "ac/erdo → 후두염(j040), 부비동염(j0180), 기관지염(j209) 상병 필요",
                "sub": "후두염/부비동염 사용 시 연결코드 기관지염 삭제해주기",
                "source": "인수인계_2026년3월.md"
            })

    # A-5. umk 필수 상병(j209 기관지염) 누락
    if "umk" in order_set:
        if dx_set and not (dx_set & UMK_REQUIRED_DX):
            results.append({
                "level": "warn",
                "message": "umk(움카민) → j209(기관지염) 상병 필요",
                "sub": "대부분의 소아 진해거담제가 기관지염에만 보험",
                "source": "소아 URI(만12세 미만).md"
            })

    # A-6. umk 소아 용량 고정 경고
    if patient_type == "소아" and "umk" in order_set:
        results.append({
            "level": "warn",
            "message": "umk 소아 용량 고정 — 벗어나면 삭감",
            "sub": "1~6세미만: 총량 9mL TID / 6~12세미만: 총량 18mL TID. Kg 무관",
            "source": "인수인계_2026년3월.md"
        })

    # A-7. tan(탄툼가글) + 하기도 상병 → 삭감
    if "tan" in order_set:
        if dx_set & TAN_BANNED_DX:
            results.append({
                "level": "err",
                "message": "tan(탄툼가글) + 하기도 상병(j22/j209) → 삭감",
                "sub": "상기도 상병, 구내염 등에만 사용 가능. 1달에 100ml 한 통만 보험",
                "source": "인수인계_2026년3월.md"
            })

    # A-8. atock/pat → j209 또는 j459 필요
    if {"atock","atock2","pat1","pat2","pat3"} & order_set:
        if dx_set and not (dx_set & ATOCK_REQUIRED_DX):
            results.append({
                "level": "warn",
                "message": "atock/pat → j209(기관지염) 또는 j459(천식) 상병 필요",
                "sub": "",
                "source": "인수인계_2026년3월.md"
            })

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # [B] NSAIDs / 진통제 룰
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # B-1. loxo + 호흡기 상병만 → 근골격계 상병 없음
    if "loxo" in order_set:
        has_resp = bool(dx_set & RESP_CODES)
        has_musculo = bool(dx_set & MUSCULO_CODES)
        if has_resp and not has_musculo:
            results.append({
                "level": "err",
                "message": "loxo + 호흡기 상병만 있음 → 삭감",
                "sub": "m545(아래허리통증) 등 근골격계 상병 추가 필요",
                "source": "인수인계_2026년3월.md"
            })

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # [B2] 약+약 삭감 (동시 보험 불가 → 하나는 f12)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # B2-1. co + cosy 동시 보험 불가 (같은 성분)
    if {"co","cosy"} <= order_set:
        results.append({
            "level": "err",
            "message": "co + cosy 동시 보험 불가 (같은 성분)",
            "sub": "하나는 f12 비급여 처리",
            "source": "네이버카페 — 감기쪽 약 2개_3개"
        })

    # B2-2. atock + pat 동시 보험 불가 (같은 분류)
    atock_codes = {"atock","atock2"}
    pat_codes = {"pat1","pat2","pat3"}
    if (order_set & atock_codes) and (order_set & pat_codes):
        results.append({
            "level": "err",
            "message": "atock + pat 동시 보험 불가 (같은 분류)",
            "sub": "하나는 f12 비급여 처리",
            "source": "네이버카페 — 감기쪽 약 2개_3개"
        })

    # B2-3. ty + semi 동시 보험 불가
    if {"ty","semi"} <= order_set or {"ty325","semi"} <= order_set or {"tykid","semi"} <= order_set:
        results.append({
            "level": "err",
            "message": "ty + semi 동시 보험 불가",
            "sub": "하나는 f12 비급여 처리",
            "source": "네이버카페 — 자주하는 지적질 모음"
        })

    # B2-4. NSAID + set 동시 보험 불가
    if (order_set & NSAID_CODES) and "set" in order_set:
        results.append({
            "level": "err",
            "message": f"NSAID + set 동시 보험 불가",
            "sub": "하나는 f12 비급여 처리. ty+set도 삭감",
            "source": "네이버카페 — 자주하는 지적질 모음"
        })

    # B2-5. d + tra 동시 보험 → tra를 trab로
    if "d" in order_set and "tra" in order_set:
        results.append({
            "level": "err",
            "message": "d(디클로페낙) + tra(트라마돌) 동시 보험 불가",
            "sub": "tra → trab(비급여)로 변경 필수. 디클로페낙이 보험",
            "source": "네이버카페 — 성인 발열시 처방"
        })

    # B2-6. 항생제 2종 동시 보험 불가
    used_ab = order_set & ANTIBIOTICS
    if len(used_ab) >= 2:
        results.append({
            "level": "err",
            "message": f"항생제 2종 동시 보험 불가: {', '.join(sorted(used_ab))}",
            "sub": "코멘트 달아도 삭감. 하나는 f12 비급여 처리",
            "source": "네이버카페 — 항생제 2종 처방시 문의"
        })

    # B2-7. 소화제(prokinetics) 2종 이상 동시 보험 불가
    used_prok = order_set & PROKINETICS
    if len(used_prok) >= 2:
        results.append({
            "level": "err",
            "message": f"소화제 {len(used_prok)}종 동시 보험 불가: {', '.join(sorted(used_prok))}",
            "sub": "macpo/dom/trime/levo/mosa 중 1종만 보험",
            "source": "네이버카페 — 자주하는 지적질 모음"
        })

    # B2-8. reba + cime 동시 보험 불가
    if "reba" in order_set and "cime" in order_set:
        results.append({
            "level": "err",
            "message": "reba + cime 동시 보험 불가",
            "sub": "하나는 f12 비급여 처리",
            "source": "네이버카페 — 자주하는 지적질 모음"
        })

    # B2-9. PPI bid/2T → 보험은 qd 1T만
    if any(c in order_set for c in ["ppi","ppi2"]):
        results.append({
            "level": "warn",
            "message": "PPI 보험은 QD 1T만 가능",
            "sub": "BID 또는 2T 처방 시 삭감. 환자 원하는 PPI 낼 때 특히 주의",
            "source": "네이버카페 — 자주하는 지적질 모음"
        })

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # [B3] 상병+약 삭감 (해당 상병으로 보험 불가 → 추가 상병 필요)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # B3-1. dexa/pd + 감기/인후두염/편도염/기관지염 → 삭감
    if {"dexa","pd"} & order_set:
        banned = dx_set & DEXA_PD_BANNED_DX
        ok = dx_set & DEXA_PD_OK_DX
        if banned and not ok:
            results.append({
                "level": "err",
                "message": f"dexa/pd + {', '.join(sorted(banned))} → 삭감",
                "sub": "j040(후두염), j303(비염), l309(피부염)에만 보험. 상병 추가 필요",
                "source": "네이버카페 — 자주하는 지적질 모음"
            })

    # B3-2. 비염(j303)에 항생제/NSAID → 삭감
    if dx_set & RHINITIS_DX:
        rhinitis_ab = order_set & ANTIBIOTICS
        rhinitis_nsaid = order_set & NSAID_CODES
        if rhinitis_ab and not (dx_set - RHINITIS_DX):
            results.append({
                "level": "err",
                "message": f"비염(j303) 단독 + 항생제({', '.join(sorted(rhinitis_ab))}) → 삭감",
                "sub": "비염에는 ty, kina만 보험. 항생제 필요 시 다른 상병 추가",
                "source": "네이버카페 — 자주하는 지적질 모음"
            })
        if rhinitis_nsaid and not (dx_set - RHINITIS_DX):
            results.append({
                "level": "err",
                "message": f"비염(j303) 단독 + NSAID({', '.join(sorted(rhinitis_nsaid))}) → 삭감",
                "sub": "비염에는 ty, kina만 보험. NSAID 필요 시 다른 상병 추가",
                "source": "네이버카페 — 자주하는 지적질 모음"
            })

    # B3-3. kina → J코드(호흡기) 아니면 삭감
    if "kina" in order_set:
        has_j = any(c.startswith("j") for c in dx_set)
        if dx_set and not has_j:
            results.append({
                "level": "err",
                "message": "kina → J코드(호흡기 상병) 없으면 삭감",
                "sub": "피부염, 중이염, 방광염 등에서 kina 삭감",
                "source": "네이버카페 — 자주하는 지적질 모음"
            })

    # B3-4. 3cefa → j00(감기)에 삭감, j060 필요
    if "3cefa" in order_set and "j00" in dx_set:
        if not (dx_set & {"j060","j040","j0390","j0180","j209"}):
            results.append({
                "level": "err",
                "message": "3cefa + j00(감기) → 삭감. j060(인후두염)으로 변경",
                "sub": "3cefa 효능효과에 비인두염(j00) 없음",
                "source": "네이버카페 — 자주하는 지적질 모음"
            })

    # B3-5. 위염에 tra/ty 삭감
    if dx_set & GASTRITIS_DX:
        if "tra" in order_set and not (dx_set - GASTRITIS_DX - {"k21","k210","k219"}):
            results.append({
                "level": "err",
                "message": "위염 상병 + tra(트라마돌) → 삭감",
                "sub": "위염 메인일 때 tra 삭감. 다른 메인 상병(감기 등) 먼저 잡기",
                "source": "네이버카페 — 자주하는 지적질 모음"
            })
        if ({"ty","ty325","tykid"} & order_set) and not (dx_set - GASTRITIS_DX):
            results.append({
                "level": "err",
                "message": "위염 상병 + ty → 삭감",
                "sub": "위염 단독일 때 ty 삭감",
                "source": "네이버카페 — 자주하는 지적질 모음"
            })

    # B3-6. 장염에 tra 삭감 (bus는 가능)
    if dx_set & ENTERITIS_DX:
        if "tra" in order_set and not (dx_set - ENTERITIS_DX):
            results.append({
                "level": "err",
                "message": "장염 상병 + tra(트라마돌) → 삭감",
                "sub": "복통에는 bus(부스코판) 사용. tra 필요 시 두통 등 상병 추가",
                "source": "네이버카페 — 자주하는 지적질 모음"
            })

    # B3-7. 바이럴 상병(인플루엔자/수족구/수두)에 항생제 → 삭감
    if dx_set & VIRAL_DX or _has_flu_dx(dx_set):
        viral_ab = order_set & ANTIBIOTICS
        if viral_ab and not (dx_set - VIRAL_DX - FLU_DX):
            results.append({
                "level": "err",
                "message": f"바이럴 상병 + 항생제({', '.join(sorted(viral_ab))}) → 삭감",
                "sub": "인플루엔자/수족구/수두 등에 항생제 보험 불가. 세균감염 의심 시 상병 추가",
                "source": "네이버카페 — 자주하는 지적질 모음"
            })

    # B3-8. 식도염에 reba → 삭감
    if dx_set & ESOPHAGITIS_DX and "reba" in order_set:
        results.append({
            "level": "err",
            "message": "식도염 + reba(무코란) → 삭감",
            "sub": "reba는 위염에만 보험. 식도염에는 al 사용 가능. 위염 상병 삭제하지 마세요",
            "source": "네이버카페 — 자주하는 지적질 모음"
        })

    # B3-9. 위염/장염에 kina → 삭감
    if (dx_set & GASTRITIS_DX or dx_set & ENTERITIS_DX) and "kina" in order_set:
        if not any(c.startswith("j") for c in dx_set):
            results.append({
                "level": "err",
                "message": "위염/장염 + kina → 삭감",
                "sub": "kina는 J코드(호흡기) 상병 필요",
                "source": "네이버카페 — 자주하는 지적질 모음"
            })

    # B3-10. w,x,y,z 상병 공단 청구 시 삭감
    if dx and len(dx) > 0:
        wxyz = [c for c in dx if c.lower().strip()[0:1] in {"w","x","y","z"}]
        if wxyz:
            results.append({
                "level": "warn",
                "message": f"w/x/y/z 상병({', '.join(wxyz)}) → 공단 청구 시 삭감",
                "sub": "비청구 환자는 코드 불필요. 청구 환자에 잡지 마세요",
                "source": "네이버카페 — 자주하는 지적질 모음"
            })

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # [C] 주사/수액 룰
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # C-1. 주사 2종 이상 → -b 코드
    used_im = order_set & IM_CODES
    if len(used_im) >= 2:
        results.append({
            "level": "warn",
            "message": f"주사제 {len(used_im)}종 → 추가분은 비급여(-b) 코드",
            "sub": f"사용 중: {', '.join(sorted(used_im))}. genta→gentab, dexa→dexab (디클로페낙 제외)",
            "source": "인수인계_2026년3월.md"
        })

    # C-2. dexa 주사 → j040(후두염) 또는 j303(비염) 필요
    if "dexa" in order_set:
        if dx_set and not (dx_set & DEXA_REQUIRED_DX):
            results.append({
                "level": "warn",
                "message": "dexa(덱사메타손) → j040(후두염) 또는 j303(비염) 상병 필요",
                "sub": "일반 감기에 dexa 쓸 때 메인상병 j040 또는 j303 포함",
                "source": "인수인계_2026년3월.md"
            })

    # C-3. genta 단순 호흡기에 사용 금지
    if "genta" in order_set:
        has_only_resp = dx_set and dx_set.issubset(RESP_CODES | MUSCULO_CODES | {"l309","l500","j303"})
        if has_only_resp:
            results.append({
                "level": "warn",
                "message": "genta(겐타마이신) → 단순 호흡기 질환에 사용하지 않음",
                "sub": "",
                "source": "인수인계_2026년3월.md"
            })

    # C-4. 소아 수액(IV) 금지
    if patient_type == "소아":
        # tamiiv는 소아에서도 6개월 이상 가능 (별도 주의)
        iv_no_tami = (order_set & IV_FLUID_CODES) - {"tamiiv","tyiv"}
        if iv_no_tami:
            results.append({
                "level": "err",
                "message": "소아(12세 미만) 수액 처방 불가",
                "sub": f"수액코드: {', '.join(sorted(iv_no_tami))}. 14~15세 이상부터 혈관상태에 따라 가능",
                "source": "소아 독감 influenza.md"
            })

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # [D] 독감/항바이러스 룰
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    used_tami = order_set & TAMIFLU_CODES
    if used_tami:
        # D-1. 타미플루 + 독감 상병(j111-1) 누락
        if dx_set and not _has_flu_dx(dx_set):
            results.append({
                "level": "warn",
                "message": "타미플루 → 독감 상병(j111-1) 확인",
                "sub": "j111-1(인플루엔자 NOS) 사용. j09-4는 2009 신종플루이므로 다름!",
                "source": "독감 influenza.md"
            })

        # D-2. 타미플루 예방목적 비보험 안내
        if not _has_flu_dx(dx_set):
            results.append({
                "level": "info",
                "message": "타미플루 예방목적(QD x10일)은 비보험",
                "sub": "치료: BID x5d(보험) / 예방: QD x10d(f12 비보험, 특정내역 삭제)",
                "source": "독감 influenza.md"
            })

        # D-3. tamiiv(페라미플루) 주의사항
        if "tamiiv" in order_set:
            results.append({
                "level": "info",
                "message": "tamiiv(페라미플루): 1회로 끝남, 5일 연속 아님",
                "sub": "성인 기본 2앰플. 6개월↑ 사용 가능. Kg당 10mL, 1앰플=150mL, 최대 300mL",
                "source": "독감 influenza.md"
            })

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # [E] 공통 안전 룰
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # E-1. dige(ranitidine) 사용 금지
    if "dige" in order_set:
        results.append({
            "level": "err",
            "message": "dige 사용 불가 — ranitidine 성분 시장 철수",
            "sub": "대체: reba(무코란) 또는 ppiiv(판타졸주사)",
            "source": "인수인계_2026년3월.md"
        })

    # E-2. 글리아티린 60세 미만
    if "glia8" in order_set:
        results.append({
            "level": "warn",
            "message": "글리아티린(glia8): 60세 미만 금기 — 나이 확인 필수",
            "sub": "반드시 전화로 확인 후 처방",
            "source": "인수인계_2026년3월.md"
        })

    # E-3. cd 상병 순서
    if "cd" in order_set:
        results.append({
            "level": "warn",
            "message": "cd(만성질환관리료) → 관련 상병이 주상병 최상위에 있어야 함",
            "sub": "고혈압/당뇨 등 만성질환 상병을 상병 목록 맨 위로",
            "source": "인수인계_2026년3월.md"
        })

    # E-4. Z코드 주상병
    if dx and len(dx) > 0:
        first_dx = dx[0].lower().strip()
        if first_dx.startswith("z") and len(dx_set) > 1:
            results.append({
                "level": "warn",
                "message": f"주상병이 배제코드({first_dx}) → 순서 변경 필요",
                "sub": "배제 상병(Z코드)은 주상병 위치에 올 수 없음",
                "source": "인수인계_2026년3월.md"
            })

    # E-5. 항생제 있는데 상병 없음
    if (order_set & ANTIBIOTICS) and not dx_set:
        results.append({
            "level": "warn",
            "message": "항생제 처방 있는데 상병코드 없음",
            "sub": f"항생제: {', '.join(sorted(order_set & ANTIBIOTICS))}",
            "source": "인수인계_2026년3월.md"
        })

    # E-6. macpo/dom → r11(구역/구토) 필수, 5일 이상 삭감
    if {"macpo","dom"} & order_set:
        if dx_set and not (dx_set & MACPO_DOM_REQUIRED_DX):
            results.append({
                "level": "err",
                "message": "macpo/dom → r11(구역/구토) 상병 필수",
                "sub": "위염/장염 코드로는 삭감. 5일 이상 처방도 삭감",
                "source": "인수인계_2026년3월.md"
            })

    # E-7. levo/mosa → r11/k30/k58만 가능 (위염/장염 삭감)
    if {"levo","mosa"} & order_set:
        if dx_set and not (dx_set & LEVO_MOSA_OK_DX):
            results.append({
                "level": "err",
                "message": "levo/mosa → r11(구역), k30(소화불량), k58(IBS)만 보험",
                "sub": "위염/장염 코드로는 삭감",
                "source": "인수인계_2026년3월.md"
            })

    # E-8. 소화성궤양용제 분류 약 중복 (reba + cime/famo 등)
    used_defense = order_set & GASTRIC_DEFENSE
    used_attack = order_set & GASTRIC_ATTACK
    # ppi + H2blocker 병용 삭감
    ppi_codes = {"ppi","ppi2","pcab"}
    h2_codes = {"cime","famo"}
    if (order_set & ppi_codes) and (order_set & h2_codes):
        results.append({
            "level": "err",
            "message": "PPI + H2 blocker(cime/famo) 병용 삭감",
            "sub": "같은 공격인자 억제 분류. reba로 대체",
            "source": "인수인계_2026년3월.md"
        })

    # E-9. al(sodium alginate) → 식도염에만 보험 (단순 위염 삭감)
    if "al" in order_set:
        if dx_set and not (dx_set & ESOPHAGITIS_DX):
            results.append({
                "level": "err",
                "message": "al(알지나) → 식도염 상병에만 보험 (2022.12.1~)",
                "sub": "단순 위염에 삭감. 연결 식도염 상병 지우지 말 것",
                "source": "인수인계_2026년3월.md"
            })

    # E-10. dupha(듀파락) 5일 이상 삭감
    if "dupha" in order_set:
        results.append({
            "level": "warn",
            "message": "dupha(듀파락) 연속 5일 이상 처방시 삭감",
            "sub": "",
            "source": "인수인계_2026년3월.md"
        })

    # E-11. sme(스멕타) → 설사 동반 상병 필요, 2세 미만 금기
    if "sme" in order_set:
        if dx_set & SME_BANNED_DX and not (dx_set & SME_OK_DX):
            results.append({
                "level": "err",
                "message": "sme + K589(IBS NOS) → 삭감. K581(IBS-D)로 변경",
                "sub": "sme는 설사 명시된 상병에만 보험",
                "source": "인수인계_2026년3월.md"
            })
        if patient_type == "소아":
            results.append({
                "level": "warn",
                "message": "sme 2세 미만 사용 불가 (2019년~). 대체: hidra",
                "sub": "",
                "source": "인수인계_2026년3월.md"
            })

    # E-12. 두드러기에 ty/kina 삭감
    if dx_set & URTICARIA_DX:
        if ({"ty","ty325","tykid"} & order_set) and not (dx_set - URTICARIA_DX):
            results.append({
                "level": "err",
                "message": "두드러기 단독 + ty → 삭감",
                "sub": "상세불명 피부염(l309) 잡으면 anti/NSAID 다 가능",
                "source": "네이버카페 — 자주하는 지적질 모음"
            })
        if "kina" in order_set and not (dx_set - URTICARIA_DX):
            results.append({
                "level": "err",
                "message": "두드러기 + kina → 삭감",
                "sub": "kina는 J코드(호흡기) 필수",
                "source": "네이버카페 — 자주하는 지적질 모음"
            })

    # E-13. 대상포진에 아시클로버 연고 → 삭감
    if dx_set & ZOSTER_DX:
        if any(c in order_set for c in ["acyoint","아시클로버연고"]):
            results.append({
                "level": "err",
                "message": "대상포진 + 아시클로버 연고 → 삭감",
                "sub": "효과 없음. 환자 원하면 f12 비청구로",
                "source": "인수인계_2026년3월.md"
            })

    # E-14. 대상포진 후 신경통 → gaba1부터, gaba3 삭감
    if any(c in order_set for c in ["gaba3","가바펜틴300"]):
        if dx_set & (ZOSTER_DX | ZOSTER_NEURALGIA_DX):
            results.append({
                "level": "err",
                "message": "gaba → gaba1부터 시작. gaba3으로 시작하면 삭감",
                "sub": "반드시 g530(대상포진 후 신경통) 상병. 대상포진과 같은 달에 잡으면 삭감",
                "source": "인수인계_2026년3월.md"
            })

    # E-15. epe(에페리손) → 경추통/요통에만 BID
    if "epe" in order_set:
        if dx_set and not (dx_set & EPE_OK_DX):
            results.append({
                "level": "err",
                "message": "epe(에페리손) → 경추통(m542)/요통(m545)에만 보험, BID만",
                "sub": "근통/염좌에 삭감",
                "source": "네이버카페 — 자주하는 지적질 모음"
            })

    # E-16. 편두통: 크래밍 + 진통제 2종 삭감
    if any(c in order_set for c in ["크래밍","cramming","ergot"]):
        pain_with_cramming = order_set & (NSAID_CODES | {"ty","ty325","semi","tykid"})
        if len(pain_with_cramming) > 1:
            results.append({
                "level": "err",
                "message": f"크래밍 + 진통제 {len(pain_with_cramming)}종 → 삭감 (해열소염진통 3종)",
                "sub": "NSAIDs/ty/semi 중 1가지만 병용. 3종부터 삭감",
                "source": "인수인계_2026년3월.md"
            })

    # E-17. 비염에 erdo/ac(가래약) 삭감
    if dx_set & RHINITIS_DX and not (dx_set - RHINITIS_DX - {"l309","l500"}):
        if {"erdo","ac"} & order_set:
            results.append({
                "level": "err",
                "message": "비염(j303) + erdo/ac(가래약) → 삭감",
                "sub": "비염에는 기침/콧물약만 가능. 가래약 필요 시 다른 상병 추가",
                "source": "인수인계_2026년3월.md"
            })

    # E-18. 장염(a090)에 NSAID(dexisy 등) 삭감
    if dx_set & ENTERITIS_DX and not (dx_set - ENTERITIS_DX):
        if order_set & NSAID_CODES:
            results.append({
                "level": "err",
                "message": f"장염 단독 + NSAID → 삭감",
                "sub": "장염에는 NSAID 보험 불가. 발열 시 ty 사용 또는 상병 추가",
                "source": "네이버카페 — 자주하는 지적질 모음"
            })

    # E-19. 위염에 NSAID 삭감
    if dx_set & GASTRITIS_DX and not (dx_set - GASTRITIS_DX - ESOPHAGITIS_DX):
        if order_set & NSAID_CODES:
            results.append({
                "level": "err",
                "message": "위염 단독 + NSAID → 삭감",
                "sub": "위염에는 NSAID 보험 불가. 다른 메인 상병 추가",
                "source": "인수인계_2026년3월.md"
            })

    # E-20. 두통에 디클로페낙/kina 삭감
    if dx_set & HEADACHE_DX and not (dx_set - HEADACHE_DX):
        if "d" in order_set:
            results.append({
                "level": "err",
                "message": "두통 단독 + d(디클로페낙) → 삭감",
                "sub": "두통에는 tra 사용. d는 근통/발열 상병 필요",
                "source": "네이버카페 — 자주하는 지적질 모음"
            })
        if "kina" in order_set:
            results.append({
                "level": "err",
                "message": "두통 + kina → 삭감",
                "sub": "kina는 J코드(호흡기) 필수",
                "source": "네이버카페 — 자주하는 지적질 모음"
            })

    # E-21. reba → k297(위염) 코드 필수
    if "reba" in order_set:
        if dx_set and not (dx_set & GASTRITIS_DX):
            results.append({
                "level": "warn",
                "message": "reba(무코란) → k297(위염) 상병 필요",
                "sub": "ppi와 함께 쓸 때도 위염 코드 지우지 말 것",
                "source": "인수인계_2026년3월.md"
            })

    # E-22. cipro → 세균성 장염(a049) 필요 (a090 삭감)
    if "cipro" in order_set and (dx_set & {"a090"}):
        if not (dx_set & {"a049","a049-1"}):
            results.append({
                "level": "err",
                "message": "cipro + a090(상세불명 장염) → 삭감",
                "sub": "cipro는 a049-1(세균성 장염) 코드 필요",
                "source": "인수인계_2026년3월.md"
            })

    # E-23. NSAIDs+semi 가능, 하지만 NSAIDs+set 삭감 (이미 B2-4에 있으나 semi 안내)
    if (order_set & NSAID_CODES) and "semi" in order_set:
        # NSAIDs + semi는 가능 → 안내만
        pass

    # E-24. 스테로이드 7일 이상 연속사용 금지
    if any(c in order_set for c in ["pd","prednisolone","dexa","dexamethasone"]):
        results.append({
            "level": "info",
            "message": "스테로이드 7일 이상 연속사용 금지",
            "sub": "",
            "source": "네이버카페 — 자주하는 지적질 모음"
        })

    # E-25. L309(피부염)에 dres 삭감
    if "dres" in order_set and "l309" in dx_set:
        results.append({
            "level": "err",
            "message": "L309(피부염) + dres(드레싱) → 삭감",
            "sub": "T793이나 S코드(상처) 잡아야 dres 가능",
            "source": "인수인계_2026년3월.md"
        })

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if not results:
        results.append({
            "level": "ok",
            "message": "체크 항목 이상 없음",
            "sub": "",
            "source": ""
        })

    return results
