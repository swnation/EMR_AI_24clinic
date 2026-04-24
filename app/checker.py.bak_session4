from typing import List, Dict
from app import drug_db

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 상수: drug_db에서 동적으로 가져옴
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ── 상병 코드 세트 (상병은 약물DB가 아니므로 여기에 유지) ──
RESP_CODES = {"j00","j040","j060","j0180","j0390","j209","j189","j303","j22","j111"}
MUSCULO_CODES = {"m545","m542","m79","m791","m792"}

# ── 진해거담제: drug_db의 _antitussive_count_rules에서 가져옴 ──
ANTITUSSIVE_ADULT = drug_db.antitussive_adult_codes()  # {"co","cosy","drop","erdo","ac"}
ANTITUSSIVE_PED = drug_db.antitussive_ped_codes()      # {"dropsy","ambsy","umk","ac2",...}
SPUTUM_ADULT = {"erdo","ac","drop"}     # 같은 분류(거담제) 병용 삭감

# ── 약품별 필수 상병 ──
AC_REQUIRED_DX = {"j040","j0180","j209"}
UMK_REQUIRED_DX = {"j209"}
ATOCK_REQUIRED_DX = {"j209","j459"}
TAN_BANNED_DX = {"j22","j209"}

# ── IM 주사제: drug_db에서 가져옴 ──
IM_CODES = drug_db.im_codes()
DEXA_REQUIRED_DX = {"j040","j303","l309","l500"}

# ── 수액: drug_db에서 가져옴 ──
IV_FLUID_CODES = drug_db.iv_fluid_codes() | {"3cefaiv","ampiiv","tamiiv","tyiv"}

# ── 타미플루: drug_db에서 가져옴 ──
TAMIFLU_CODES = drug_db.tamiflu_codes()
FLU_DX = {"j111","j111-1","j09","j10","j11"}

# ── 항생제: drug_db에서 가져옴 ──
ANTIBIOTICS = drug_db.antibiotics_codes()

# ── 약+약 삭감 ──
NSAID_CODES = drug_db.nsaid_codes()
AAP_CODES = drug_db.aap_codes()

# ── 소화제: drug_db에서 가져옴 ──
PROKINETICS = drug_db.prokinetics_codes()

# ── 상병+약 삭감 (상병 코드는 약물DB가 아니므로 여기에 유지) ──
DEXA_PD_BANNED_DX = {"j00","j060","j0390","j209"}
DEXA_PD_OK_DX = {"j040","j303","l309","l500"}
RHINITIS_DX = {"j303"}
KINA_REQUIRED_PREFIX = "j"
VIRAL_DX = {"j111","j111-1","b084","b08","b01","b019"}
GASTRITIS_DX = {"k297","k29","k290","k295","k296"}
ENTERITIS_DX = {"a09","a090","a099","k529"}
ESOPHAGITIS_DX = {"k210","k219","k21"}
HEADACHE_DX = {"r51"}
GASTRIC_DEFENSE = {"reba"}
GASTRIC_ATTACK = {"cime","famo","ppi","ppi2","pcab"}
MACPO_DOM_REQUIRED_DX = {"r11"}
LEVO_MOSA_OK_DX = {"r11","k30","k58","k580","k581","k582","k589"}
TRIME_OK_DX = {"r11","k30","k58","k580","k581","k589","k297","k29","a090","a084","a049"}
ZOSTER_DX = {"b029","b02"}
ZOSTER_NEURALGIA_DX = {"g530"}
URTICARIA_DX = {"l500","l501","l509","l50"}
EPE_OK_DX = {"m542","m545","m543","m544"}
SME_OK_DX = {"a090","a084","a049","k581"}
SME_BANNED_DX = {"k589"}
TRA_BANNED_DX = {"a090","a084","a049","k58","k30","r11","k297","k29","k296"}

# ── 추가 상수 (N 시리즈 룰) ──
DM_DX_PREFIX = ("e10","e11","e12","e13","e14")
SYRUP_CODES = {"cosy","cough","codsy","syna10","syna15","levt","pel"}
DYSLIPIDEMIA_DX = {"e780","e781","e782","e783","e784","e785"}
ANTIPLATELET_CODES = {"asp","ast","clopi"}
ANTIHISTAMINE_CODES = {"ceti","cetisy","levoceti","fexo","olo","hls","phen","uxsy","keto","keto2","bepo"}
NSAID_ANALGESIC_ALL = {"loxo","dexi","dexi4","dexisy","bru","dic","cereb","melox",
                       "ty","ty325","ty160","ty80","semi","set","d"}
NONINSURANCE_DRUG_CODES = {"contrav","phenter","orlistat","fin1","fina1",
                           "palpal","palpal1","palpal2","sil","sil2","siladepil","sildenapil","silf",
                           "cial10","cial20","tadaday",
                           "nolevo","ellaone","levono"}
DEMENTIA_DX_PREFIX = ("f00","f01","f02","f03","g30")
BURN_FACE_HAND_CODES = {"bdres2"}
HF_DX = {"i500","i501","i509","i50","i110","i130","i132"}

# ── PDF 스캔 추가 상수 ──
STOMATITIS_DX = {"k121","k1211","k122","k120"}
STATIN_CODES = {"ato10","ato20","ato40","ato80","rosu1","rosu2","rosu3",
                "sim1","sim2","simva","atoam","otpt"}
GLAUCOMA_DX_PREFIX = ("h40","h42")
BPH_DX = {"n400","n401","n402","n403","n409","n40"}
COLCHICINE_CODES = {"콜킨","colchi"}


def _dx_startswith(dx_set: set, prefix: str) -> bool:
    return any(c.startswith(prefix) for c in dx_set)


def _has_flu_dx(dx_set: set) -> bool:
    if dx_set & FLU_DX:
        return True
    return _dx_startswith(dx_set, "j09") or _dx_startswith(dx_set, "j10") or _dx_startswith(dx_set, "j11")


def _append(results: list, level: str, message: str, sub: str = "", source: str = ""):
    """결과 추가 헬퍼"""
    results.append({"level": level, "message": message, "sub": sub, "source": source})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# [A] 진해거담제 룰
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _check_antitussive(dx_set: set, order_set: set, patient_type: str, results: list):
    # A-1. 성인 진해거담제 초과 (상기도 2종, 하기도 3종)
    if patient_type != "소아":
        used = order_set & ANTITUSSIVE_ADULT
        lower_resp = dx_set & {"j22","j209"}
        limit = 3 if lower_resp else 2
        if len(used) > limit:
            _append(results, "err",
                f"진해거담제 {len(used)}종 → {'하기도 3종' if lower_resp else '상기도 2종'}까지만 보험",
                f"사용 중: {', '.join(sorted(used))}. suda는 카운팅 제외",
                "인수인계_2026년3월.md")

    # A-2. 성인 같은 분류(sputum) 약물 중복 → 삭감
    if patient_type != "소아":
        used_sputum = order_set & SPUTUM_ADULT
        if len(used_sputum) >= 2:
            _append(results, "err",
                f"거담제(sputum) 중복: {', '.join(sorted(used_sputum))} → 삭감",
                "같은 분류(erdo/ac/drop) 병용 불가. 하나는 f12 비급여 처리",
                "인수인계_2026년3월.md")

    # A-3. 소아 진해거담제 초과 (6세미만 3종, 6세이상 2종)
    if patient_type == "소아":
        used = order_set & ANTITUSSIVE_PED
        if len(used) > 3:
            _append(results, "err",
                f"소아 진해거담제 {len(used)}종 → 삭감",
                "6세미만 3종, 6세이상 2종까지. suda2는 카운팅 제외",
                "소아 URI(만12세 미만).md")

    # A-4. ac/erdo/drop → 비염(j303) 단독이면 삭감. 다른 호흡기 상병 필요
    if {"ac","erdo","drop"} & order_set:
        has_resp_not_rhinitis = dx_set & (RESP_CODES - RHINITIS_DX)  # j303 제외한 호흡기 상병
        if dx_set and not has_resp_not_rhinitis:
            only_rhinitis = dx_set & RHINITIS_DX
            if only_rhinitis:
                _append(results, "err",
                    "ac/erdo/drop + 비염(j303) 단독 → 삭감",
                    "비염에 가래약 불가. j00/j060/j0390/j209 등 다른 호흡기 상병 추가 필요",
                    "인수인계_2026년3월.md")
            elif not any(c.startswith("j") for c in dx_set):
                _append(results, "warn",
                    "ac/erdo/drop → 호흡기 상병(J코드) 필요",
                    "j00(감기)/j060(인후두염)/j0390(편도염)/j209(기관지염) 등",
                    "인수인계_2026년3월.md")

    # A-5. umk 필수 상병(j209 기관지염) 누락
    if "umk" in order_set:
        if dx_set and not (dx_set & UMK_REQUIRED_DX):
            _append(results, "warn",
                "umk(움카민) → j209(기관지염) 상병 필요",
                "대부분의 소아 진해거담제가 기관지염에만 보험",
                "소아 URI(만12세 미만).md")

    # A-6. umk 소아 용량 고정 경고
    if patient_type == "소아" and "umk" in order_set:
        _append(results, "warn",
            "umk 소아 용량 고정 — 벗어나면 삭감",
            "1~6세미만: 총량 9mL TID / 6~12세미만: 총량 18mL TID. Kg 무관",
            "인수인계_2026년3월.md")

    # A-7. tan(탄툼가글) + 하기도 상병 → 삭감
    if "tan" in order_set:
        if dx_set & TAN_BANNED_DX:
            _append(results, "err",
                "tan(탄툼가글) + 하기도 상병(j22/j209) → 삭감",
                "상기도 상병, 구내염 등에만 사용 가능. 1달에 100ml 한 통만 보험",
                "인수인계_2026년3월.md")

    # A-8. atock/pat → j209 또는 j459 필요
    if {"atock","atock2","pat1","pat2","pat3"} & order_set:
        if dx_set and not (dx_set & ATOCK_REQUIRED_DX):
            _append(results, "warn",
                "atock/pat → j209(기관지염) 또는 j459(천식) 상병 필요",
                "", "인수인계_2026년3월.md")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# [B] NSAIDs / 진통제 / 약+약 삭감 룰
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _check_pain_and_conflicts(dx_set: set, order_set: set, patient_type: str, results: list):
    # B-1. loxo + 호흡기 상병만 → 근골격계 상병 없음
    if "loxo" in order_set:
        has_resp = bool(dx_set & RESP_CODES)
        has_musculo = bool(dx_set & MUSCULO_CODES)
        if has_resp and not has_musculo:
            _append(results, "err",
                "loxo + 호흡기 상병만 있음 → 삭감",
                "m545(아래허리통증) 등 근골격계 상병 추가 필요",
                "인수인계_2026년3월.md")

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



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# [B3] 상병+약 삭감
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _check_dx_drug_conflicts(dx_set: set, order_set: set, dx: list, patient_type: str, results: list):
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



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# [C] 주사/수액 룰
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _check_injection(dx_set: set, order_set: set, patient_type: str, results: list):
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



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# [D] 독감/항바이러스 룰
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _check_flu(dx_set: set, order_set: set, results: list):
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



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# [E] 공통 안전 룰
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _check_common(dx_set: set, order_set: set, dx: list, patient_type: str, results: list):
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
            "sub": "고혈압/당뇨/갑상선/수면제/편두통 등 만성질환 상병을 상병 목록 맨 위로",
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

    # E-6. mac/macpo/dom → r11(구역/구토) 필수, 5일 이상 삭감
    if {"mac","macpo","dom"} & order_set:
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

    # E-26. dexa + 당뇨(E10~E14) 금기
    dm_dx = {c for c in dx_set if c.startswith("e10") or c.startswith("e11") or c.startswith("e14")}
    if dm_dx and "dexa" in order_set:
        results.append({
            "level": "err",
            "message": "dexa(덱사메타손) + 당뇨 상병 → 금기",
            "sub": "DM 환자 스테로이드 사용 시 혈당 상승 위험",
            "source": "인수인계_2026년3월.md"
        })

    # E-27. d(디클로페낙) 처방 시 자동입력 기타근통 삭제 금지 안내
    if "d" in order_set:
        results.append({
            "level": "info",
            "message": "d(디클로페낙) → 자동입력 '기타 근통' 코드 삭제 금지",
            "sub": "연결코드로 m79108 자동 입력됨. 특별한 경우 아니면 지우지 말 것",
            "source": "인수인계_2026년3월.md"
        })

    # E-28. 12세 이상 소아약(시럽/가루) 보험 안 됨
    PED_DRUG_CODES = {"augsy","cefasy","clarisy","3cefasy","typow","tysy","dropsy",
                      "ac2","suda2","dexisy","cetisy","tamisy","ambsy","umk","lukasy"}
    if patient_type != "소아":
        used_ped = order_set & PED_DRUG_CODES
        if used_ped:
            results.append({
                "level": "warn",
                "message": f"소아약({', '.join(sorted(used_ped))}) → 12세 이상 보험 안 됨",
                "sub": "성인약 처방 후 용법에 <pow> 입력하면 갈아서 복용 가능",
                "source": "네이버카페 — 자주하는 지적질 모음"
            })

    # E-29. suda2 + cetisy/uxsy 병용 주의 (pheniramine 중복)
    if "suda2" in order_set and ({"cetisy","uxsy"} & order_set):
        results.append({
            "level": "warn",
            "message": "suda2 + cetisy/uxsy 병용 주의",
            "sub": "suda2에 pheniramine 포함 → 항히스타민 성분 중복",
            "source": "인수인계_2026년3월.md"
        })

    # E-30. ephed(리노에바스텔) 최대 10일
    if "ephed" in order_set:
        results.append({
            "level": "warn",
            "message": "ephed(리노에바스텔) → 최대 10일까지만",
            "sub": "suda 용량 높아 부작용 주의",
            "source": "인수인계_2026년3월.md"
        })

    # E-31. luka 천식 처방 시 특정내역 변경 필요
    if any(c in order_set for c in ["luka10","luka4","luka5","lukasy"]) and (dx_set & {"j459","j459-1","j46"}):
        results.append({
            "level": "info",
            "message": "luka + 천식 → 특정내역 변경 필요",
            "sub": "'타 천식 약제로 증상조절이 되지 않는 2단계 이상의 천식'으로 수정",
            "source": "인수인계_2026년3월.md"
        })

    # E-32. 복통에 tra 삭감 → bus 사용
    if "tra" in order_set and not dx_set:
        # 이미 E-5에서 항생제 상병없음 체크하므로 여기선 패스
        pass

    # E-33. 향정신성의약품 중복 처방 불가 (zol + 식욕억제제 등)
    PSYCHOTROPIC = {"zol","스틸녹스","디에타민","큐시미아"}
    used_psycho = order_set & PSYCHOTROPIC
    if len(used_psycho) >= 2:
        results.append({
            "level": "err",
            "message": "향정신성의약품 중복 처방 불가",
            "sub": f"사용 중: {', '.join(sorted(used_psycho))}. 수면제+식욕억제제 등 절대 금기",
            "source": "인수인계_2026년3월.md"
        })

    # E-34. mosa → r11(구역) 또는 k30(소화불량) 연결코드 필요
    if "mosa" in order_set and dx_set:
        if not (dx_set & {"r11","k30","k58","k580","k581","k589"}):
            results.append({
                "level": "warn",
                "message": "mosa → r11(구역) 또는 k30(소화불량) 연결코드 필요",
                "sub": "",
                "source": "인수인계_2026년3월.md"
            })

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # [N] 추가 룰 (knowledge 전수 스캔 결과)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    dm_dx = {c for c in dx_set if c.startswith(DM_DX_PREFIX)}

    # N1. 당뇨 + suda/suda2 (pseudoephedrine) → 금기
    if dm_dx and ({"suda","suda2"} & order_set):
        _append(results, "err",
            "당뇨 + pseudoephedrine(suda/suda2) → 금기",
            "혈당 상승 + 혈압 상승 위험. 콧물약 대체 필요",
            "당뇨 Diabetes DM.md")

    # N2. 당뇨 + 시럽제제 → 당류 포함 지양
    if dm_dx and (order_set & SYRUP_CODES):
        used = order_set & SYRUP_CODES
        _append(results, "warn",
            f"당뇨 + 시럽제제({', '.join(sorted(used))}) → 당류 포함, 알약 권장",
            "시럽에 당류 함유. 가능하면 정제/캡슐로 대체",
            "당뇨 Diabetes DM.md")

    # N5. bisoprolol 2.5mg → 심부전 상병 필요
    if "bisop25" in order_set or "콩코르2.5" in order_set:
        if not (dx_set & HF_DX):
            _append(results, "err",
                "bisoprolol 2.5mg → 심부전 상병 필수",
                "5mg은 고혈압 가능. 2.5mg은 심부전(I50) 상병 있어야 보험",
                "인수인계_2026년3월.md")

    # N7. 이상지질혈증 + cd → cd 비대상
    if "cd" in order_set and (dx_set & DYSLIPIDEMIA_DX):
        has_cd_eligible = any(c.startswith(("i10","i11","i12","i13","i15",  # 고혈압
                                            "e10","e11","e12","e13","e14",  # 당뇨
                                            "g43"))                         # 편두통
                             for c in dx_set)
        if not has_cd_eligible:
            _append(results, "warn",
                "이상지질혈증은 cd(만성질환관리료) 비대상",
                "고혈압/당뇨/편두통 등 다른 cd 대상 상병이 있어야 cd 청구 가능",
                "인수인계_2026년3월.md")

    # N14. clopidogrel 단독(asp 없이) → i252/i638 필요
    if "clopi" in order_set and not ({"asp","ast"} & order_set):
        if not (dx_set & {"i252","i638"}):
            _append(results, "err",
                "clopidogrel 단독 → i252(만성허혈심질환) 또는 i638(뇌혈관질환) 상병 필요",
                "aspirin 없이 clopi 단독 사용시 해당 상병 필수",
                "항혈소판제.md")

    # N9. fibrate + omega3 병용 → TG약 1제만
    fibrate_codes = {"feno","fib"}
    omega3_codes = {"오마코","om3"}  # 오마코 등 원내코드 확인 필요
    if (order_set & fibrate_codes) and (order_set & omega3_codes):
        _append(results, "err",
            "fibrate + omega3 병용 → TG약 1제만 인정",
            "하나는 전액본인부담(삭감)",
            "고지혈증 이상지질혈증.md")

    # N12. 항히스타민 2/3세대 2종 이상 → 삭감 (1세대+2/3세대는 허용)
    gen1_ah = {"phen","uxsy"}  # 1세대
    used_ah = order_set & ANTIHISTAMINE_CODES
    used_gen23 = used_ah - gen1_ah  # 2/3세대만
    if len(used_gen23) >= 2:
        _append(results, "err",
            f"항히스타민(2/3세대) {len(used_gen23)}종 동시 → 1종만 보험: {', '.join(sorted(used_gen23))}",
            "1세대(phen)+2/3세대 병용은 가능. 2/3세대끼리 2종 삭감",
            "항히스타민제 정리.md")

    # N13. 항혈소판제 2종 동시 삭감
    used_ap = order_set & ANTIPLATELET_CODES
    if len(used_ap) >= 2:
        _append(results, "err",
            f"항혈소판제 2종 동시 삭감: {', '.join(sorted(used_ap))}",
            "항혈소판제 2종 병용은 무조건 삭감",
            "인수인계_2026년3월.md")

    # N32. 해열소염진통제 계열 3종 이상 삭감
    used_pain = order_set & NSAID_ANALGESIC_ALL
    if len(used_pain) >= 3:
        _append(results, "err",
            f"해열소염진통제 {len(used_pain)}종 → 3종부터 삭감: {', '.join(sorted(used_pain))}",
            "NSAIDs + AAP + tramadol 합쳐서 2종까지",
            "인수인계_2026년3월.md")

    # N15. co(코데날) 12세 미만 사용 금기
    if patient_type == "소아" and "co" in order_set:
        _append(results, "err",
            "co(코데날) → 12세 미만 사용 금기",
            "codeine 포함 제제. 소아는 dropsy/umk 등 사용",
            "소아 독감 influenza.md")

    # N16. 소아 + d(디클로페낙) → 5세 미만은 di(비급여)
    if patient_type == "소아" and "d" in order_set:
        _append(results, "warn",
            "소아 d(디클로페낙) → 5세 미만은 di(비급여코드) 사용",
            "5세 이상부터 d(급여). 체중별 용량: 10kg=0.2, 15kg=0.25, 20kg=0.33, 30kg=0.5",
            "소아 URI.md")

    # N17. 소아 dexisy + 장염 단독 → 추가 상병 필요
    if patient_type == "소아" and "dexisy" in order_set:
        if (dx_set & ENTERITIS_DX) and not (dx_set - ENTERITIS_DX):
            _append(results, "warn",
                "소아 dexisy + 장염 단독 → r5099(FUO) 또는 r51(두통) 추가 필요",
                "장염에 NSAID 삭감. 발열/두통 상병 추가",
                "소아 AGE FGID.md")

    # N19. PCAB(pcab) + PPI/H2 병용 금지
    if "pcab" in order_set:
        ppi_h2 = order_set & {"ppi","ppi2","cime","famo"}
        if ppi_h2:
            _append(results, "err",
                f"PCAB(위캡) + {', '.join(sorted(ppi_h2))} 병용 금지",
                "PCAB은 PPI/H2 blocker와 병용 불가. 1회 최대 4주까지만 보험",
                "인수인계_2026년3월.md")

    # N21. famotidine 용량별 필수 상병
    # famo는 20mg. 현재 용량 구분 못하므로 일반 안내
    if "famo" in order_set:
        if not (dx_set & (GASTRITIS_DX | ESOPHAGITIS_DX | {"k25","k26","k27","k28"})):
            _append(results, "warn",
                "famo(파모티딘) → 위염/식도염/궤양 상병 필요",
                "20mg QD는 위염 가능. 40mg QD 또는 20mg BID는 궤양/GERD 코드 필요",
                "인수인계_2026년3월.md")

    # N22. macpo/dom 5일 이상 삭감 안내
    if {"macpo","dom"} & order_set:
        _append(results, "info",
            "macpo/dom → 5일 이상 연속 처방시 삭감",
            "단기간만 사용. 장기 필요시 trime/mosa로 변경",
            "인수인계_2026년3월.md")

    # N25. 비급여 전용 약 + 보험접수 경고
    used_nonins = order_set & NONINSURANCE_DRUG_CODES
    if used_nonins:
        _append(results, "err",
            f"비급여 전용약({', '.join(sorted(used_nonins))}) → 일반접수 전용",
            "비만/발기부전/사후피임/탈모 약은 보험접수 불가. j00 감기코드로 일반접수",
            "인수인계_2026년3월.md")

    # N27. zolpidem(zol) 최대 28일
    if "zol" in order_set:
        _append(results, "warn",
            "zol(졸피뎀) → 최대 28일까지만 처방 가능",
            "향정신성의약품. 다른 향정신성의약품(식욕억제제 등)과 절대 중복 불가",
            "인수인계_2026년3월.md")

    # N29. 치매 상병 + 약 처방 → 비급여 전용
    dementia_dx = {c for c in dx_set if c.startswith(DEMENTIA_DX_PREFIX)}
    if dementia_dx and (order_set - {"cd"}):
        _append(results, "err",
            "치매 상병 + 약 처방 → 1차기관 보험 불가",
            "아리셉트(도네페질) 등 초처방 절대 불가. 비급여 전용",
            "치매 관련 약들 dementia.md")

    # N30. 베니톨(치질약) 최장 7일
    if "베니톨" in order_set or "benytol" in order_set:
        _append(results, "warn",
            "베니톨(치질약) → 최장 7일까지만 인정",
            "장기사용시 정맥임파부전 상병 필요",
            "인수인계_2026년3월.md")

    # N31. 화상 bdres2 → 수족지/안면/경부/성기 부위 상병 필수
    if "bdres2" in order_set:
        burn_face_dx = {c for c in dx_set if c.startswith(("t20","t21","t22","t23","t24","t25"))}
        if not burn_face_dx:
            _append(results, "warn",
                "bdres2(화상드레싱-수족지/안면) → 해당 부위 화상 상병 필수",
                "수족지/안면/경부/성기 포함 화상 상병 없으면 삭감",
                "화상 Burn.md")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # [P] 카페 PDF 스캔 기반 추가 룰
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # P1. simvastatin + clarithromycin 병용 금기 (drug interaction)
    if ({"sim1","sim2","simva"} & order_set) and ({"clari","clari2"} & order_set):
        _append(results, "err",
            "simvastatin + clarithromycin 병용 금기 (횡문근융해 위험)",
            "스타틴 복용자에 clari 금기. augmentin/cefaclor 등으로 대체",
            "고지혈증 _ 네이버 카페.pdf")

    # P2. itraconazole + statin 병용 금기
    if "itraco" in order_set and (order_set & STATIN_CODES):
        _append(results, "err",
            "itraconazole + statin 병용 금기",
            "이트라코나졸 복용 중 스타틴 금기",
            "약제 부작용 및 금기 _ 네이버 카페.pdf")

    # P3. clarithromycin + colchicine 병용 금기
    if ({"clari","clari2"} & order_set) and (order_set & COLCHICINE_CODES):
        _append(results, "err",
            "clarithromycin + colchicine 병용 금기",
            "콜히친 독성 증가 위험",
            "약제 부작용 및 금기 _ 네이버 카페.pdf")

    # P4. 구내염에 suda/erdo/kina 삭감
    if dx_set & STOMATITIS_DX:
        bad_in_stom = order_set & {"suda","suda2","erdo","ac","kina"}
        if bad_in_stom and not (dx_set - STOMATITIS_DX - {"k297"}):
            _append(results, "err",
                f"구내염 + {', '.join(sorted(bad_in_stom))} → 삭감",
                "구내염에는 NSAID/스테로이드/항생제/탄툼만 가능",
                "구내염 상병 처방약 _ 네이버 카페.pdf")

    # P5. suda + 녹내장 금기
    glaucoma_dx = {c for c in dx_set if c.startswith(GLAUCOMA_DX_PREFIX)}
    if glaucoma_dx and ({"suda","suda2"} & order_set):
        _append(results, "err",
            "suda(pseudoephedrine) + 녹내장 → 금기",
            "폐쇄각 녹내장 환자 pseudoephedrine 금기",
            "약제 부작용 및 금기 _ 네이버 카페.pdf")

    # P6. bus + 녹내장 금기
    if glaucoma_dx and "bus" in order_set:
        _append(results, "err",
            "bus(부스코판) + 녹내장 → 금기",
            "항콜린제 녹내장 환자 금기",
            "약제 부작용 및 금기 _ 네이버 카페.pdf")

    # P7. 항히스타민/co/bus + BPH 금기 (요저류)
    bph_dx = dx_set & BPH_DX
    if bph_dx:
        bph_bad = order_set & {"phen","pheni","co","cosy","bus","uxsy"}
        if bph_bad:
            _append(results, "warn",
                f"BPH(전립선비대) + {', '.join(sorted(bph_bad))} → 요저류 위험",
                "1세대 항히스타민/코데날/부스코판은 전립선비대 환자 금기",
                "약제 부작용 및 금기 _ 네이버 카페.pdf")

    # P8. 1도 화상에 bdres(화상처치) 삭감 → dres만 가능
    if "bdres1" in order_set:
        burn_1st = {c for c in dx_set if c.startswith("t30") or "1도" in str(c)}
        if not any(c.startswith(("t20","t21","t22","t23","t24","t25")) for c in dx_set):
            _append(results, "warn",
                "화상처치(bdres) → 2도 이상 + 부위 특정 화상 상병 필요",
                "1도 화상이면 dres(단순처치)만 가능. 화상NOS도 삭감",
                "상처와 화상 _ 네이버 카페.pdf")

    # P9. PPI + 위염만 → 비보험 안내
    ppi_in_order = order_set & {"ppi","ppi2","pcab","ol1","ol2","ol+"}
    if ppi_in_order:
        has_gastritis_only = (dx_set & GASTRITIS_DX) and not (dx_set & (ESOPHAGITIS_DX | {"k25","k26","k27","k28"}))
        if has_gastritis_only:
            _append(results, "warn",
                f"PPI({', '.join(sorted(ppi_in_order))}) → 위염에 비보험, 식도염/궤양 상병 필요",
                "PPI는 식도염(k21)/궤양(k25~k28)에만 보험. 위염만으로는 삭감",
                "위염과 식도염(PPI) _ 네이버 카페.pdf")

    # P10. reba + ppi 병용 가능 확인 (안내)
    # (이미 reba+cime 삭감은 B2-8에 있음. reba+ppi는 가능이므로 별도 룰 불필요)

    # P11. dres + 이물제거술 병용 삭감
    if "dres" in order_set and any(c in order_set for c in ["이물제거","이물"]):
        _append(results, "err",
            "이물제거술 + dres(단순처치) → dres 삭감",
            "이물제거술에 드레싱 포함. 별도 청구 불가",
            "자주하는 지적질 모음 _ 네이버 카페.pdf")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # [F] 피드백 55개 전수 스캔 기반 추가 룰
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # F1. r53(권태 및 피로) 보험 불가 (6회+ 반복)
    if "r53" in dx_set:
        _append(results, "err",
            "r53(권태 및 피로) → 보험 청구 불가 상병",
            "수액 보험 시 다른 증상 상병 필요. 비청구 또는 질환 상병으로 변경",
            "피드백 2022~2025 반복")

    # F2. 항생제 + j00(감기) 단독 → 변경 권장 (5회+ 반복)
    if (order_set & ANTIBIOTICS) and "j00" in dx_set:
        if not (dx_set & {"j060","j040","j0390","j0180","j209"}):
            _append(results, "warn",
                "항생제 + j00(감기) 단독 → j060(인후두염) 등으로 변경 권장",
                "j00에 항생제 비권장 (병원 평가 불이익). j060/j0390/j0180/j209로",
                "피드백 2022~2025 반복")

    # F3. NSAIDs 2종 동시 삭감 (5회+ 반복)
    used_nsaid_only = order_set & {"loxo","dexi","dexi4","dexisy","bru","dic","cereb","melox","d"}
    if len(used_nsaid_only) >= 2:
        _append(results, "err",
            f"NSAIDs 2종 동시 삭감: {', '.join(sorted(used_nsaid_only))}",
            "같은 계열(NSAIDs) 2종 동시 보험 불가. 하나는 f12 또는 semi/ty로 대체",
            "피드백 2022~2025 반복")

    # F4. 진해/거담제 + 호흡기 상병(J코드) 없음 (7회+ 반복)
    resp_drugs = order_set & {"co","cosy","codsy","drop","erdo","ac","suda","syna10","syna15"}
    if resp_drugs:
        has_j = any(c.startswith("j") for c in dx_set)
        if dx_set and not has_j:
            _append(results, "err",
                f"호흡기약({', '.join(sorted(resp_drugs))}) → J코드(호흡기 상병) 없음 → 삭감",
                "co/erdo/drop/suda 등은 호흡기 상병(j00/j060/j209 등) 필요",
                "피드백 2022~2025 반복")

    # F5. 항히스타민 + 필수 상병 없음 (6회+ 반복)
    used_antiH = order_set & {"bepo","olo","ceti","cetisy","fexo","levoceti","hls","keto","keto2"}
    if used_antiH:
        ah_ok_dx = {"j303","l309","l500","l501","l509","l239","b029","b02","h101"}
        if dx_set and not (dx_set & ah_ok_dx):
            _append(results, "warn",
                f"항히스타민({', '.join(sorted(used_antiH))}) → 비염/피부염/알러지 상병 필요",
                "j303(비염), l309(피부염), l500(두드러기), b029(대상포진) 중 하나",
                "피드백 2022~2025 반복")

    # F6. cipro + 방광염 → n12-3 신우신염 필요 (4회+ 반복)
    if "cipro" in order_set and (dx_set & {"n300","n309","n390"}):
        if not any(c.startswith("n12") for c in dx_set):
            _append(results, "err",
                "cipro + 방광염 1차 사용 → n12-3(신우신염) 상병 추가 필요",
                "cipro는 2차 항생제. 방광염 1차 aug2 권장. cipro 시 신우신염 코드 필요",
                "피드백 2022~2025 반복")

    # F7. tra(트라마돌) 12세 미만 금기 (2회 반복)
    if patient_type == "소아" and "tra" in order_set:
        _append(results, "err",
            "tra(트라마돌) → 12세 미만 사용 금기",
            "소아 통증에는 ty/dexisy 사용",
            "피드백 2022~2023")

    # F8. tirop 필수 상병 (3회 반복)
    if "tirop" in order_set:
        tirop_ok = {"k297","k29","k290","k295","k296","a090","a084","a049","k30","k58","k580","k581"}
        if dx_set and not (dx_set & tirop_ok):
            _append(results, "warn",
                "tirop → k297(위염)/a090(장염)/k30(소화불량) 등 상병 필요",
                "", "피드백 2024~2025 반복")

    # F9. trime 필수 상병 체크 (4회 반복) — TRIME_OK_DX 상수는 있었으나 체크 로직 없었음
    if "trime" in order_set:
        if dx_set and not (dx_set & TRIME_OK_DX):
            _append(results, "warn",
                "trime → k297(위염)/a090(장염)/r11(구역)/k30(소화불량)/k58(IBS) 상병 필요",
                "trime은 범위 넓지만 식도염(k21)에는 삭감",
                "피드백 2024~2025 반복")

    # F10. 수액 단독(주사제 믹스 없음) 경고 (4회+ 반복)
    iv_in_order = order_set & (IV_FLUID_CODES | {"mc","gw3","gw6","gw8","gw10","gw15","egw"})
    im_in_order = order_set & IM_CODES
    if iv_in_order and not im_in_order:
        _append(results, "info",
            "수액 단독 → 주사제(tra 등) 믹스 권장",
            "치료 목적 증명 + 실비 분쟁 방지. URI는 tra 트라덱사 반반 믹스",
            "피드백 2022~2025 반복")

    # F11. bus + tra 동시 보험 불가 (3회 반복)
    if "bus" in order_set and "tra" in order_set:
        _append(results, "err",
            "bus(부스코판) + tra(트라마돌) 둘 다 보험 → 삭감",
            "tra → trab(비급여)로 변경",
            "피드백 2024 반복")

    # F12. r11 + k30 동시 불필요 (3회+ 반복)
    gi_symptom_dx = dx_set & {"r11","r111","r113","k30"}
    if len(gi_symptom_dx) >= 2:
        _append(results, "info",
            f"r11(구역)/k30(소화불량) 동시 불필요: {', '.join(sorted(gi_symptom_dx))}",
            "mosa/levo는 셋 중 하나만, mac/macpo는 r11만 필요. 하나만 잡으세요",
            "피드백 2022~2025 반복")

    # F13. macpo 18세 미만 보험 불가
    if patient_type == "소아" and "macpo" in order_set:
        _append(results, "err",
            "macpo → 18세 미만 보험 불가 (항암 후 구역만 인정)",
            "macb(비급여) 또는 dom2(소아용)/trimesy로 변경",
            "피드백 2024")

    # F14. luka 필수 상병 (비염/천식) 체크
    luka_codes = order_set & {"luka10","luka5","luka4","lukasy","lukabid"}
    if luka_codes:
        luka_ok = {"j303","j459","j459-1","j46"}
        if dx_set and not (dx_set & luka_ok):
            _append(results, "warn",
                f"luka({', '.join(sorted(luka_codes))}) → j303(비염) 또는 j459(천식) 상병 필요",
                "", "피드백 2024")

    # F15. pd(프레드니솔론) 필수 상병
    if "pd" in order_set:
        pd_ok = {"j040","j303","l309","l500","l501","j459","j46"}
        banned = dx_set & DEXA_PD_BANNED_DX
        ok = dx_set & pd_ok
        if dx_set and not ok and not banned:
            _append(results, "warn",
                "pd(프레드니솔론) → j040(후두염)/j303(비염)/l309(피부염) 등 상병 필요",
                "감기/인후두염/편도염/기관지염에 pd 삭감. 보험 가능 상병 확인",
                "피드백 2024~2025 반복")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 메인 진입점
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _build_order_map(order_details: list) -> Dict[str, dict]:
    """order_details를 code→info dict로 변환"""
    if not order_details:
        return {}
    return {o["code"].lower().strip(): o for o in order_details}


def _check_dosage(dx_set: set, order_set: set, order_map: Dict[str, dict],
                  patient_type: str, age: int, results: list):
    """용량/일수 기반 체크 (order_details가 있을 때만 동작)"""
    if not order_map:
        return

    # D-macpo/dom 5일 이상 삭감
    for code in ["macpo", "dom"]:
        if code in order_map:
            days = order_map[code].get("days")
            if days and days >= 5:
                _append(results, "err",
                    f"{code} → {days}일 처방 → 5일 이상 삭감",
                    "macpo/dom은 단기간(5일 미만)만 사용",
                    "인수인계_2026년3월.md")

    # D-dupha 5일 이상 삭감
    if "dupha" in order_map:
        days = order_map["dupha"].get("days")
        if days and days >= 5:
            _append(results, "err",
                f"dupha → {days}일 → 5일 이상 연속 삭감",
                "", "인수인계_2026년3월.md")

    # D-zolpidem 28일 초과
    if "zol" in order_map:
        days = order_map["zol"].get("days")
        if days and days > 28:
            _append(results, "err",
                f"zol → {days}일 → 최대 28일 초과",
                "향정신성의약품 처방일수 제한",
                "인수인계_2026년3월.md")

    # D-항생제 10일 초과
    ab_in_order = order_set & drug_db.antibiotics_codes()
    for code in ab_in_order:
        if code in order_map:
            days = order_map[code].get("days")
            if days and days > 10:
                _append(results, "warn",
                    f"{code} → {days}일 → 항생제 10일 초과",
                    "항생제 최대 10일. clari 연속 10일 초과 시 변경 필요",
                    "약물 최대 처방일수.pdf")

    # D-ephed 10일 초과
    if "ephed" in order_map:
        days = order_map["ephed"].get("days")
        if days and days > 10:
            _append(results, "err",
                f"ephed → {days}일 → 최대 10일 초과",
                "리노에바스텔 최대 10일까지만",
                "인수인계_2026년3월.md")

    # D-PPI QD 1T만 (freq/dose 체크)
    for ppi_code in ["ppi", "ppi2", "pcab", "ol1", "ol2", "ol+"]:
        if ppi_code in order_map:
            freq = order_map[ppi_code].get("freq")
            dose = order_map[ppi_code].get("dose")
            if freq and freq > 1:
                _append(results, "err",
                    f"{ppi_code} → {freq}회/일 → BID 삭감. QD 1T만 보험",
                    "", "인수인계_2026년3월.md")
            if dose and dose > 1:
                _append(results, "err",
                    f"{ppi_code} → {dose}T → 2T 이상 삭감. QD 1T만 보험",
                    "", "인수인계_2026년3월.md")


def run_check(dx: List[str], orders: List[str], symptoms: str, patient_type: str,
              order_details: list = None, age: int = None) -> List[Dict]:
    dx_set = {c.lower().strip() for c in dx}
    order_set = {c.lower().strip() for c in orders}
    order_map = _build_order_map(order_details)
    results: List[Dict] = []

    _check_antitussive(dx_set, order_set, patient_type, results)
    _check_pain_and_conflicts(dx_set, order_set, patient_type, results)
    _check_dx_drug_conflicts(dx_set, order_set, dx, patient_type, results)
    _check_injection(dx_set, order_set, patient_type, results)
    _check_flu(dx_set, order_set, results)
    _check_common(dx_set, order_set, dx, patient_type, results)
    _check_dosage(dx_set, order_set, order_map, patient_type, age or 0, results)

    if not results:
        _append(results, "ok", "체크 항목 이상 없음")

    return results
