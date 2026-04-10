"""
차팅 템플릿 + 진단서/소견서 양식
knowledge/오더와_차팅_진단서_예시.txt 기반
"""

# ── 진료의뢰서 템플릿 ──
REFERRAL_TEMPLATES = [
    {
        "id": "referral_general",
        "name": "진료의뢰서 — 일반",
        "category": "진료의뢰서",
        "template": (
            "상기 환자 {주소}로 본원 내원한 환자로\n"
            "상기 증상에 대한 further evaluation and proper management 위해 "
            "귀원으로 전원하오니\n"
            "고진선처 부탁드립니다\n"
            "감사합니다"
        ),
        "fields": ["주소"]
    },
    {
        "id": "referral_appendicitis",
        "name": "진료의뢰서 — R/O Appendicitis",
        "category": "진료의뢰서",
        "template": (
            "R/O Acute appendicitis\n"
            "R/O Mesenteric lymphadenitis\n\n"
            "상기 환자 내원 당일 시작된 복부통증 주소로 본원 내원한 환자로 "
            "내원시 실시한 이학적 검사상 우하복부의 압통 관찰 됩니다\n"
            "이에 R/O Acute appendicitis 에 대한 further evaluation and "
            "proper management 위해 귀원으로 전원하오니\n"
            "고진선처 부탁드립니다\n"
            "감사합니다"
        ),
        "fields": []
    },
    {
        "id": "referral_no_improvement",
        "name": "진료의뢰서 — 대증치료 후 호전 없음",
        "category": "진료의뢰서",
        "template": (
            "상기 환자 {주소}로 본원 내원한 환자로\n"
            "대증치료 이후에도 증상호전 보이지 않아\n"
            "상기 증상에 대한 further evaluation and proper management 위해 "
            "귀원으로 전원하오니\n"
            "고진선처 부탁드립니다\n"
            "감사합니다"
        ),
        "fields": ["주소"]
    },
]

# ── 진단서/소견서 템플릿 ──
DIAGNOSIS_TEMPLATES = [
    {
        "id": "dx_general",
        "name": "진단서 — 일반",
        "category": "진단서",
        "template": (
            "상기 환자는 지난 {날짜} 내원 {기간} 전부터 시작된 {증상}을 "
            "주소로 내원하였으며 상기 진단 의심 하에 투약 시작하였습니다.\n"
            "향후 최소 {일수}일 이상의 안정가료가 필요하며 "
            "경과에 따라 추가 검사 및 치료가 요구될 수 있습니다."
        ),
        "fields": ["날짜", "기간", "증상", "일수"]
    },
    {
        "id": "dx_uri",
        "name": "소견서 — URI/감기",
        "category": "진단서",
        "template": (
            "상기 환자 {날짜} {증상} 등의 증상으로 본원 내원한 환자로\n"
            "내원 당시 실시한 검사상 {진단명} 진단 받았음.\n"
            "이후 {일수}일 간의 치료, 안정 가료 및 추적 관찰 필요함.\n\n"
            "단, 상기 증상은 초진소견에 한하며 이후 증상호전이 보이지 않거나\n"
            "타증상 발현시 추가적인 진찰 및 검사가 필요할 수 있음"
        ),
        "fields": ["날짜", "증상", "진단명", "일수"]
    },
    {
        "id": "dx_gastroenteritis",
        "name": "진단서 — 장염",
        "category": "진단서",
        "template": (
            "상기 환자는 {날짜} 내원 {기간} 전부터 시작된 "
            "발열, 복통, 오심, 설사 등의 장염 증상을 주소로\n"
            "내원한 환자로, 본원에서 실시한 이학적 검사상 "
            "세균성 장염 진단명 의심하에 투약 시작하였습니다.\n"
            "또한 조속한 증상 개선을 위해 치료적 목적의 수액치료를 병행하였습니다."
        ),
        "fields": ["날짜", "기간"]
    },
    {
        "id": "dx_rti",
        "name": "진단서 — 상기도감염",
        "category": "진단서",
        "template": (
            "상기 환자는 {날짜} 내원 {기간} 전부터 시작된 "
            "몸살, 근육통, 인후통, 콧물, 코막힘, 기침 등의 상기도 감염 증상을\n"
            "주소로 내원한 환자로, 본원에서 실시한 이학적 검사상 "
            "급성 비인두염 진단명 의심하에 투약 시작하였습니다.\n"
            "또한 조속한 증상 개선을 위해 치료적 목적의 수액치료를 병행하였습니다."
        ),
        "fields": ["날짜", "기간"]
    },
]

# ── 독감 관련 템플릿 ──
FLU_TEMPLATES = [
    {
        "id": "flu_dx_oseltamivir",
        "name": "독감 소견서 — oseltamivir (5일 투약)",
        "category": "독감",
        "template": (
            "상기 환자는 {날짜} 내원 {기간}부터 시작된 "
            "{증상} 등을 주소로 내원하였으며\n"
            "본원에서 시행한 검사 상 influenza type {A/B}로 진단되어 "
            "oseltamivir 항바이러스제 5일간 투약 시작하였습니다.\n"
            "질병관리청에서 정한 지침에 따라 '정상체온으로 복귀 후 24시간'까지는 "
            "격리가 필요하며 일반적으로 약 5일정도 소요됩니다.\n"
            "따라서 {격리종료일}까지의 격리가 예상됩니다.\n"
            "다만 그 이전에 발열 증상 호전되고 24시간 경과시 미리 격리해제 가능합니다.\n"
            "또한 경과에 따라 추가 검사 및 치료가 요구될 수 있습니다."
        ),
        "fields": ["날짜", "기간", "증상", "A/B", "격리종료일"]
    },
    {
        "id": "flu_dx_peramivir",
        "name": "독감 소견서 — peramivir (수액)",
        "category": "독감",
        "template": (
            "상기 환자는 {날짜} 내원 {기간}부터 시작된 "
            "{증상} 등을 주소로 내원하였으며\n"
            "본원에서 시행한 검사 상 influenza type {A/B}로 진단되어 "
            "peramivir 항바이러스제 수액 치료 진행하였습니다.\n"
            "질병관리청에서 정한 지침에 따라 '정상체온으로 복귀 후 24시간'까지는 "
            "격리가 필요하며, 일반적으로 5일정도 소요됩니다.\n"
            "따라서 {격리종료일}까지의 격리가 예상됩니다.\n"
            "다만 그 이전에 발열 증상 호전되고 24시간 경과시 미리 격리해제 가능합니다.\n"
            "또한 경과에 따라 추가 검사 및 치료가 요구될 수 있습니다."
        ),
        "fields": ["날짜", "기간", "증상", "A/B", "격리종료일"]
    },
    {
        "id": "flu_release",
        "name": "독감 격리해제 소견서",
        "category": "독감",
        "template": (
            "상기 환자 {진단일} 고열 기침 인후통 주소로 본원 내원하여\n"
            "{A/B}형 독감 - Influenza type {A/B} 진단받고\n"
            "5일간의 항바이러스제 치료 및 자가격리, 안정가료 등의 치료 받은 환자로\n"
            "{호전일} 내원 당시 발열 인후통 등의 증상 호전 보이고\n"
            "{격리해제일} 이후 전염력은 거의 소실 된 것으로 판단됩니다\n\n"
            "이에 자가격리 더이상 필요치 않으며 단체 생활 가능한 것으로 판단됩니다"
        ),
        "fields": ["진단일", "A/B", "호전일", "격리해제일"]
    },
]

# ── 기타 소견서 ──
OTHER_TEMPLATES = [
    {
        "id": "htn_work_clearance",
        "name": "소견서 — 고혈압 업무 가능",
        "category": "기타",
        "template": (
            "상기 남환은 본원에서 고혈압으로 약제 치료 받고 계시는 분으로, "
            "금일 내원시 혈압 {혈압} mmHg이며 평소에도 정상 수치 유지되고 있습니다.\n"
            "따라서 일상적인 근무가 가능할 것으로 판단됩니다."
        ),
        "fields": ["혈압"]
    },
    {
        "id": "covid_pcr_referral",
        "name": "진료의뢰서 — COVID-19 PCR",
        "category": "기타",
        "template": (
            "상기 환자는 {기간} 전부터 시작된 발열, 인후통, 코막힘, 콧물, 기침, "
            "두통, 근육통을 주소로 내원하였으며\n"
            "COVID-19 PCR 검사가 필요하다고 사료되어 의뢰드리오니 "
            "고진선처 부탁드립니다.\n"
            "감사합니다."
        ),
        "fields": ["기간"]
    },
]

# ── 주사/수액 오더 안내 ──
ORDER_GUIDES = [
    {
        "id": "order_im",
        "name": "주사 오더 — 라이브톡 전송 형식",
        "category": "오더가이드",
        "template": (
            "'환자명' 주사명 IM\n"
            "'환자명' 수액실\n"
            "'환자명' 주사명 IM 후 수액실\n"
            "'환자명' 트라덱사 반반 IV"
        ),
        "fields": []
    },
    {
        "id": "order_iv_notice",
        "name": "수액 — 실비 안내 주의",
        "category": "오더가이드",
        "template": (
            "수액 절대로 실비 된다고 하지 마세요.\n"
            "보험사와 환자 간의 문제이며, 우리는 질환에 맞는 치료에 맞는 수액만 사용한다고 해주세요.\n"
            "대신 보험사에서 요구하는 서식에는 최대한 맞춰서 해줄 수 있다고만 해주시면 됩니다.\n\n"
            "'치료목적의 수액 사용', 격리 기간 명시 등 서술이 필요한 경우 → '소견서', '진단서' 서식으로만 나갑니다.\n"
            "절대 진료확인서와 같은 다른 서식에 대충 적어서 주지 마세요."
        ),
        "fields": []
    },
]

# 전체 템플릿 모음
ALL_TEMPLATES = (
    REFERRAL_TEMPLATES +
    DIAGNOSIS_TEMPLATES +
    FLU_TEMPLATES +
    OTHER_TEMPLATES +
    ORDER_GUIDES
)

def get_all_templates():
    """모든 템플릿 목록 반환"""
    return ALL_TEMPLATES

def get_template_by_id(template_id: str):
    """ID로 특정 템플릿 반환"""
    for t in ALL_TEMPLATES:
        if t["id"] == template_id:
            return t
    return None

def get_templates_by_category(category: str):
    """카테고리별 템플릿 목록"""
    return [t for t in ALL_TEMPLATES if t["category"] == category]
