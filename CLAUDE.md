# EMR_AI_24clinic — 프로젝트 브리핑

## 한 줄 요약
의사랑 EMR 화면을 F12로 스캔 → 상병/오더 자동 체크 → 삭감 경고 + 차팅 템플릿 제공하는 로컬 Python 앱

---

## 핵심 목적
24시 열린의원(서울 송파구)에서 스케줄제로 근무하는 **신규 GP들의 EMR 실수를 줄이는 보조 도구**.
진단·처방 자체를 AI가 대신하는 게 아니라, 이미 입력된 내용이 **우리 병원 기준에 맞게 작성됐는지** 체크하고 표준화된 양식을 제시하는 것이 목표.

### 하지 않는 것
- ❌ 진단 제안 (의사 판단 영역)
- ❌ 처방 자동 생성
- ❌ 환자 정보 수집/저장
- ❌ 외부 서버 전송 (로컬 전용)

---

## 기술 스택
- OS: Windows 11, Python 3.x
- 서버: FastAPI (uvicorn) → localhost:8080
- UI: 브라우저 HTML/JS (의사랑 옆에 항상 띄워둠)
- OCR: Windows WinRT OCR (한국어, 별도 설치 불필요)
- 캡처: pyautogui
- 코드보정: rapidfuzz
- 단축키: keyboard (F12)
- 테스트: pytest
- LLM(나중에): Ollama + EXAONE or Qwen2.5

---

## 의사랑 화면 스캔 대상 (v3: 9영역으로 확장됨)

세션3 에서 기존 4영역 → 9영역으로 확장. 상세는 `decision-2026-04-21-capture-regions-and-rules.md` 참조.

핵심 4영역 (세션2 부터):
1. 증상 탭 — 차팅 텍스트
2. 특이증상 탭 — 과거력/특이사항
3. 상병 코드 목록 — ICD 코드들
4. 오더 목록 — 약품코드 + 용량/일수

세션3 추가 5영역:
5. 환자 인적사항 (나이, 성별 등)
6. Vital signs (BST, BW 등)
7. 기타 추후 확정

---

## 핵심 운영 규칙 (knowledge/ 파일 기반)

### 상병 순서
1. 만성질환 (cd 필요) → 최상위
2. IM 제제 관련 상병
3. 주상병
4. 기타

### 오더 순서
1. IM 주사 → 2. IV 수액 → 3. PO 내복 (만성→일반) → 4. 외용제 → 5. 검사

### 주사제 규칙
- IM/IV 구분 없이 모두 IM으로 등록
- **2종 이상 → 추가분은 -b 코드** (gentab, dexab 등. 디클로페낙 제외)

---

## 현재 구현된 체크 룰

### Legacy 룰 (rules/rules.json v0.3 — 세션5 에서 v3 스키마 마이그레이션 예정)

| 룰 | 레벨 | 내용 |
|----|------|------|
| loxo + 호흡기 상병만 | ERR | m545 등 근골격계 상병 추가 필요 |
| cipro 방광염 1차 | ERR | n12-3 신우신염 상병 추가 필요 |
| levofloxacin 500mg+ QD | ERR | 삭감. 250mg QD x10d만 인정 |
| 신우신염+디클로페낙 | WARN | 자동입력 기타근통 코드 삭제 필요 |
| 모누롤산 | WARN | 반드시 1,1,1 처방 |
| 소아 cipro/levo | ERR | quinolone 금기 |
| cd 상병 순서 | WARN | 주상병 최상위 확인 |
| 주사 2종+ | WARN | -b 코드 사용 |
| 성인 진해거담제 2종 초과 | ERR | 삭감 |
| 소아 진해거담제 초과 | ERR | 6세미만 3종, 이상 2종 |
| umk 소아 용량 | WARN | 1~6세 9mL, 6~12세 18mL 고정 (→ pediatric-formulation-dose 에 포함) |
| glia8 60세 미만 | WARN | 금기, 전화확인 필수 |
| 만성질환 재진 | INFO | 수동 변경 필요 |

### 신규 룰 (app/rules_v2/, 세션4 — v3 §8.4 스키마)

| rule_id | purpose | severity | trigger | 내용 |
|---|---|---|---|---|
| `pediatric-formulation-dose` | safety | info/warn/unknown | patient-context+vitals+order | 12세 미만 소아 시럽/가루약 curated list 기반 용량 검증 (18개 약, 8개 정밀 + 10개 needs_review) |
| `bst-code-missing` | non_reversible_error | warn | vitals+order | BST 값 있음 + 'bst' 오더 코드 누락 |
| `bst-value-missing` | omission | warn | vitals+order | 'bst' 오더 있음 + BST 측정값 누락 |
| `bst-ocr-uncertain` | non_reversible_error | unknown | vitals+order | BST 값 / 오더 OCR 불명확 (통합 unknown) |

**현재 발동 조건**: `vitals_context` / `patient_context` 가 `run_check()` 에 전달돼야 실질 발동.
아직 `main.py` 가 넘기지 않으므로 Legacy 파이프라인 호환 경로에서 조용히 skip. 세션5 에서 연결 예정.

### 다음 세션 이후 구현 예정

- `quinolone-pediatric-contraindication` — cipro 18세 미만 / eyelevo 1세 미만 금기
- `pediatric-dexibuprofen-gi-dx` — dexisy 위장염 상병 제한 (R51/R509-2 필요)
- `pediatric-formulation-respiratory-dx` — dropsy / ambsy / umk / atock2 기관지염 상병 필요
- `tysy-dexisy-matching-dose-hint` — 병용 시 같은 용량 권유 (보호자 편의)

### 기존 "추가 필요한 룰" (미구현, 7번 마이그레이션 사전 분류 대상)

- 당뇨: HbA1c 3개월 이내 중복 삭감 / 단순확인 → 배제된 상병 처리
- 고혈압: bisoprolol 2.5mg → 심부전 상병 필요 / 항혈소판제 2종 삭감
- 이상지질혈증: cd 비대상 (만성질환관리료 청구 안 됨)
- 골다공증: 매 방문 명세서 필수 / 1년 이내 검사 결과 필요
- 편두통: 크래밍 + NSAIDs/ty/semi 중 1가지만 (2종부터 삭감)
- clopidogrel 단독 → i252 또는 i638 상병 필요
- dige 코드 사용불가 (ranitidine 성분) → reba/ppiiv로 대체
- 배제된 상병 → 주상병으로 사용 불가

---

## 주요 약품 코드

```
항생제:  aug2=아목클625  cefa=세플러  cipro=에프로신  levo=크라비트250
         clari=클래마신  augsy=하이크라듀오(amox 40 mg/mL + clav 5.7)
         cefasy=소아용세파시럽
진통제:  loxo=록스파인  dexi=덱시파인  ty=세토펜이알서방  ty325=AAP 325mg
         semi=무파인세미
위장약:  reba=무코란  ppi=에스오엠20mg  ppiiv=판타졸주사
주사제:  tra=타마돌  d=디클로페낙  genta=겐타마이신  dexa=덱사메타손
         pheni=클로르페니라민  linco=린코마이신  ambi=암브록솔
수액:    ns=NS250kit  ns110=중외엔에스110cc  mc=마이어스칵테일
         3cefaiv=세프트리악손1g IV  gw6/8/10/15=영양수액
소아약:  typow=세토펜건조시럽  tysy=세토펜현탁(acetaminophen 32 mg/mL)
         dexisy=코코페디(dexibuprofen 12 mg/mL)
         dropsy=레드보르시럽  ac2=이태란과립  suda2=코비안에시럽
         umk=움카민시럽 (1~6세 9mL TID, 6~12세 18mL TID 고정)
만성약:  cd=만성질환관리료  glia8=콜리아티린(60세↑만)
측정:    bst=혈당측정 (소문자 고정)

DEPRECATED: tykid (단종, ty325 로 대체)
```

상세는 `rules/pediatric_drug_list.json` 참조.

---

## 개발 단계

### Phase 1 — OCR 파이프라인 (Windows 전용, 로컬 이전 후)
1. ✅ calibrate.py: 의사랑 9개 영역 좌표 저장 (세션3)
2. ⬜ capture.py: F12 → 영역 캡처 + forbidden_zone 검증
3. ⬜ reader.py: Windows OCR 텍스트 추출
4. ⬜ parser.py: 코드 파싱 + fuzzy 보정 + vitals_context / patient_context 반환

### Phase 2 — 룰 확장 + UI
5. ✅ (세션4) 신규 룰 3개 추가 — BST / 소아 제형 용량
6. ⬜ (세션5) rules.json v0.3 → v3 §8.4 스키마 마이그레이션
   - 선행 작업: legacy 청구/삭감 rule 재분류 (drop / non_reversible_error / safety / keep-as-legacy)
7. ⬜ parser.py / server.py 가 vitals_context / patient_context 를 run_check() 에 전달하도록 연결
8. ⬜ frontend 차팅 템플릿 복사 기능
9. ⬜ 진단서/소견서 양식 템플릿

### Phase 3 — LLM
10. Ollama 연동 (롱테일/복합 케이스)
11. knowledge/ RAG 질문 응답

---

## 프로젝트 구조

```
EMR_AI_24clinic/
├── app/
│   ├── __init__.py
│   ├── checker.py                # run_check() — 세션4 패치로 vitals_context/patient_context 파라미터 추가
│   ├── server.py                 # FastAPI
│   ├── drug_db.py
│   ├── templates.py
│   ├── id_utils.py               # 세션3: session_id/patient_key/local_salt
│   ├── export_dataset.py         # 세션3: Transmission-level PHI 방어선
│   └── rules_v2/                 # 세션4: 신규 룰 모듈
│       ├── __init__.py
│       ├── schema.py             # v3 §8.4 RuleResult
│       ├── age_utils.py          # 16구간 + 12세 미만 판정
│       ├── vitals_utils.py       # OCR 관대 파싱 (coerce_float / vital_state)
│       ├── bst.py                # Rule-BST-1/2 + bst-ocr-uncertain
│       └── pediatric_dose.py     # Rule-Pediatric-Formulation-Dose
├── ocr/
│   ├── calibrate.py              # 세션3: 9영역 캘리브레이션
│   ├── capture.py                # F12 캡처
│   ├── parser.py                 # OCR 결과 파싱
│   ├── reader.py                 # Windows OCR
│   ├── forbidden_zone.py         # 세션3: Capture-level PHI 방어선
│   ├── experiment.py
│   └── regions.json              # calibrate.py 가 생성
├── rules/
│   ├── rules.json                # Legacy v0.3 (세션5 마이그레이션 예정)
│   └── pediatric_drug_list.json  # 세션4: 18개 약 curated list
├── scripts/
│   └── session4_checker_patch.py # 세션4: checker.py 자동 패치 도구
├── tests/
│   └── test_rules_v2.py          # 세션4: pytest 70건
├── data/, frontend/, knowledge/, 피드백/
├── main.py                       # 진입점
├── CLAUDE.md                     # 이 파일
└── README.md
```

---

## 실행

```bash
pip install -r requirements.txt

# 세션4 패치 적용 (최초 1회)
python scripts/session4_checker_patch.py --dry-run
python scripts/session4_checker_patch.py

# 검증
pytest -q tests/test_rules_v2.py    # → 70 passed 기대

# 앱 실행
python main.py                      # → http://localhost:8080
python ocr/calibrate.py             # 최초 영역 설정 (진료실 PC)
```

---

## 주의
- 환자 정보 LLM 전송 금지 — 상병코드/오더코드만 처리
- OCR 오인식 → rapidfuzz score 85 이상만 매칭
- 의사랑 레이아웃 변경 시 calibrate.py 재실행
- BST 오더 코드는 소문자 `"bst"` 고정 (세션4 확정)
- augsy 원내 1일 상한 30 mL (의학적 금기 아님, 관행). 의학적 상한은 amoxicillin 90 mg/kg/day

---

## 진행 이력

| 세션 | 날짜 | 성과 | 상태 |
|---|---|---|---|
| 1~2 | ~2026-04 초 | v1→v2→v3 설계 |  |
| 3 | 2026-04-24 | id_utils / calibrate / forbidden_zone / export_dataset 4개 모듈 (Patch A+) | 완료 |
| 4 | 2026-04-24 | app/rules_v2/ 신규 룰 패키지 3개 rule + 자동 patch 스크립트 + pytest 70건 (GPT 3차 승인) | 완료 |
| 5 | 예정 | rules.json v3 스키마 마이그레이션 + 파이프라인 연결 (vitals_context/patient_context) |  |
