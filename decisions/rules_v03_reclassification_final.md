---
id: rules-v03-reclassification-final
project: clinical-assist
type: decision-record
status: approved
session: 5
created: 2026-04-25
reviewed_by: [붕쌤 2026-04-25]
related:
  - rules/rules.json
  - rules/pediatric_drug_list.json
---

# Legacy `rules.json` v0.3 재분류 최종안

## 개요

`rules/rules.json` v0.3 의 21개 legacy rule 을 v1 범위에 맞게 재분류한다.

세션4/5 원칙:

- v1 은 청구 자동화를 하지 않는다.
- 순수 삭감/상병 누락/비급여 처리 안내 rule 은 drop 한다.
- 환자 안전, 사후 수정 곤란 오류, 원내 표준 clinical policy 만 남긴다.
- drop rule 은 삭제하지 않고 archive metadata 로 보존한다.

## 분류 축

| 분류 | 정의 | v3 마이그레이션 |
|---|---|---|
| safety | 의학적 안전, 시장 철수약, medication-use error 방지 | `purpose=safety` |
| clinical_policy | 의학적 절대 금기는 아니나 원내 표준 진료·설명·운영 원칙상 일관되게 안내해야 하는 항목 | `purpose=clinical_policy` |
| non_reversible_error | 사후 수정 곤란한 실수 | 해당 없음 |
| drop | 순수 청구/삭감 자동화 + 급여 기준 | archive 보존 |

## v1 마이그레이션 대상

### Safety 2개

| legacy id | v1 rule_id | severity | 비고 |
|---|---|---|---|
| `tamiiv_info` | `tamiiv-single-dose` | info | tamiiv 1회 투여 안내 |
| `dige_banned` | `dige-market-withdrawn` | warn | ranitidine 시장 철수약 처방 방지 |

### Clinical Policy 1개

| legacy id | v1 rule_id | severity | 비고 |
|---|---|---|---|
| `ped_iv_ban` | `ped-iv-ban` | warn | 만 12세 미만 IV 수액 원내 제한. tamiiv도 제한 대상 |

`ped_iv_ban` 정정 사항:

- 의학적 절대 금기가 아니라 24시열린의원 원내 운영 규칙이다.
- `tamiiv`는 예외가 아니다. IV 수액이므로 동일하게 제한 대상이다.
- 따라서 `purpose=safety`가 아니라 `purpose=clinical_policy`로 둔다.

## Drop 18개

`adult_antitussive_over2`, `adult_sputum_dup`, `ped_antitussive_over`, `ac_erdo_required_dx`, `umk_required_dx`, `umk_dose`, `tan_lower_resp`, `atock_pat_dx`, `loxo_resp`, `inj_2types`, `dexa_required_dx`, `genta_resp_ban`, `tamiflu_dx`, `tamiflu_prophylaxis`, `glia8_age`, `cd_order`, `z_code_primary`, `antibiotics_no_dx`.

특수 메타:

- `ped_antitussive_over`: Batch 2 소아 다제병용 safety rule 후보.
- `umk_dose`: `Rule-Pediatric-Formulation-Dose`가 대체. 1세 미만은 payer_notice 후보.
- `genta_resp_ban`: latent safety + Batch 2 재검토 후보.
- `glia8_age`: payer_notice 후보.

## Followup

### F2 payer_notice plane

`glia8_age`, `umk` 1세 미만처럼 의학적 금기가 아니라 급여/본인부담/환자 설명 이슈인 항목은 core rule engine에 섞지 않고 별도 `payer_notice` plane 후보로 보존한다.

### F5 infection_control clinical policy module

격리기간, 등원·등교, 직장 복귀, 소견서/진단서 문구는 core `rules/rules.json`에 hard-code하지 않는다.

별도 데이터 중심 모듈로 설계한다.

```text
rules/clinical_policy/
  infection_control/isolation_policies.json
  certificate_templates/isolation_certificates.json
  patient_instructions/*.json
```

초기 seed 후보: 수두, 인플루엔자, 수족구병, 코로나19.

수두 예시: 전체 병변이 가피화되면 격리 해제 가능하며 평균 5–7일 소요. 단, 실제 운영 문구는 최신 공식 지침 확인 후 확정한다.
