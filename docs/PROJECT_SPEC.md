# 인트윈 제안 자동화 플랫폼 기획서 v0.2

## 0. v0.2 방향 전환 요약

이 문서의 기존 v0.1 내용은 “과거 PPT 장표를 슬라이드 단위로 분해·라벨링·검색해서 새 제안서에 합치는 장표 라이브러리”를 1차 목표로 삼았다.
v0.2부터 1차 목표는 다음과 같이 바뀐다.

> 공고문·과업지시서와 입찰서식/사업 카드의 확정 정보를 바탕으로, 사람이 고른 기존 제안서 PPTX 템플릿의 디자인은 그대로 두고 텍스트만 바꿔 새 제안서 초안을 만든다.

따라서 이 섹션이 아래 v0.1 내용과 충돌할 때는 이 섹션을 우선한다.

### v0.2 핵심 원칙

1. AI는 슬라이드 디자인, 아이콘, 도식, 레이아웃, 색 조합을 새로 만들지 않는다.
2. AI는 PPTX 안에서 추출된 텍스트 슬롯(텍스트 박스, 표 셀, 노트 등)의 글만 바꾼다.
3. 새 제안서 텍스트의 근거는 공고문/과업지시서, 사업 카드, 입찰서식/HWPX 기반 정보, 회사 DB다.
4. 금액, 날짜, 기관명, 인력, 수행 실적처럼 사실 정보는 AI가 만들지 않는다. 근거가 없으면 `[확인 필요]`로 둔다.
5. 사실 슬롯(사업명, 기관명, 기간, 참여 인력, 수행 실적 등)은 AI가 문장을 쓰지 않고 필드 연결만 제안한다. 실제 값은 코드가 `bid_context`·`project_card`·DB에서 그대로 치환한다.
6. 서술 슬롯(추진전략, 수행방법, 기대효과 등)만 AI가 문장을 쓴다. 출력 후 숫자, 날짜, 고유명사가 입력 근거 안에 있는지 자동 검사한다.
7. 공고문·과업지시서·배점표는 자유 요약보다 요구사항 번호, 출처, 배점 항목 목록으로 저장한다.
8. 템플릿 PPT는 완성된 제안서 한 벌이 아니라 장표 유형 모음으로 본다. 배점표 항목별로 어떤 유형을 몇 장 쓸지 `outline`을 먼저 정하고 슬롯을 채운다.
9. 기존 장표 라이브러리, 유사 과업 검색, 여러 PPT 합치기는 후순위 확장 기능이다. 장표 라이브러리는 나중에 `outline` 단계에서 배점표 항목에 맞는 장표 유형을 추천하는 기능으로 이어진다.

### v0.2 MVP 흐름

1. 사용자가 공고문/과업지시서 텍스트 또는 파일을 넣는다.
2. 사업 카드에 기관명, 사업명, 기간, 분야 등 확정 정보를 입력한다.
3. 입찰서식 기반 정보 또는 간단한 입찰정보 폼을 입력한다.
4. 사용자가 기존 제안서 PPTX를 템플릿으로 선택한다.
5. 시스템이 PPTX의 텍스트 슬롯을 추출하고, 디자이너/사용자가 템플릿당 한 번 슬롯 이름과 유형(`fact`/`narrative`/`fixed`)을 확정한다.
6. 사용자가 배점표 항목별 개요(`outline`: 항목 → 장표 유형 → 장 수)를 정한다. M1에서는 사람이 입력하고, 이후 AI/라이브러리 추천으로 확장한다.
7. AI가 공고문 요구사항과 입찰정보를 바탕으로 사실 슬롯의 필드 연결과 서술 슬롯의 텍스트 교체안을 만든다.
8. 사람이 교체안과 필드 연결을 확인·수정한다.
9. 원본 템플릿 복사본에 확정 텍스트만 적용한다. 사실 슬롯은 코드가 JSON 값을 그대로 넣고, 서술 슬롯은 확정 문장을 적용해서 `data/outputs/`에 새 PPTX를 만든다.
10. 잔존 기관명·지역명·사업명, 새로 생긴 숫자·날짜·고유명사, 요구사항 누락, 금지 표현, `[확인 필요]`, 넘침 위험을 리포트한다.

### v0.2 데이터 모델 추가/변경

기존 `projects`, `documents`, `jobs`, `ai_calls`, `usage_events`는 유지한다. 아래 개념을 우선 추가한다.

```
notice_contexts
  project_id
  source_document_id
  raw_text
  requirements            jsonb: [{req_id, title, detail, source_page, source_text, scoring_item_key}]
  scoring_items           jsonb: [{key, name, points, source_page}]
  summary                 jsonb: 보조 정보. 자유 요약은 요구사항 목록을 대체하지 않는다.
  status                  draft | confirmed

bid_contexts
  project_id
  source_document_id
  data                    jsonb: 회사 일반 현황, 참여 인력, 수행 실적, 입찰서식 값
  status                  draft | confirmed

templates
  project_id
  document_id
  name
  status                  pending | analyzed | failed
  slide_count
  preview_path

template_text_slots
  template_id
  slide_index
  shape_id
  kind                    text_box | table_cell | placeholder | notes
  role_key                cover_title | background | strategy | method | schedule | company | unknown
  slot_name               사람이 붙인 안정적인 이름. 예: slot_project_name, slot_strategy_body
  value_type              fact | narrative | fixed
  field_binding           fact 슬롯일 때 연결할 JSON 경로. 예: project_card.name, bid_context.personnel[0].name
  original_text
  char_count
  max_char_count          원래 글자 수와 슬롯 크기 기반 권장 상한
  bounds                  jsonb: {x, y, w, h}
  style_ref               jsonb
  locked

outlines
  project_id
  template_id
  status                  draft | confirmed
  items                   jsonb: [{scoring_item_key, slide_type_key, slide_count, requirement_ids, template_slide_refs}]

generated_decks
  project_id
  template_id
  outline_id
  title
  status                  draft | generating | review | building | ready | failed
  output_path
  report                  jsonb

deck_text_rewrites
  deck_id
  slot_id
  value_type              fact | narrative | fixed
  field_binding
  original_text
  suggested_text
  final_text
  requirement_ids         이 슬롯/장표가 다루는 요구사항
  status                  pending | accepted | edited | rejected | failed
  warnings                jsonb
```

### v0.2 마일스톤 개요

| 단계 | 내용 | 수준 | 마일스톤 |
| --- | --- | --- | --- |
| P1 | 템플릿 기반 PPT 생성: 공고/과업 입력, 사업 카드, 입찰정보, PPTX 텍스트 슬롯 추출, AI 텍스트 교체, 검증, 새 PPTX 출력 | 실사용 | M0~M7 |
| P2 | 입찰서식(HWPX) 채우기와 PPT 생성 입력으로 재사용 | 실사용 | M8~M9 |
| P3 | 템플릿/과거 자료 검색, 유사 과업 추천, 별표 | 실사용 | M10 |
| P4 | 나라장터 공고 탐색·추천, 구글 드라이브·로그인, 사무실 PC 배포 | 데모/운영 | M11~M12 |

### v0.2 화면 개요

| 경로 | 내용 |
| --- | --- |
| `/projects` | 사업 카드 목록·필터, 새 카드 만들기 |
| `/projects/[id]` | 카드 상세: 정보 편집, 입력 자료, 템플릿, 생성 결과 |
| `/projects/[id]/inputs` | 공고문·과업지시서·입찰정보 입력/확인 |
| `/templates` | 템플릿 PPTX 목록, 업로드, 분석 상태, 미리보기 |
| `/decks/[id]/rewrite` | 텍스트 교체안 확인·수정 |
| `/decks/[id]` | 생성 상태, 리포트, 다운로드 |
| `/forms` | HWPX 서식 채우기 |
| `/company` | 회사 데이터(인력, 실적) 입력 |

---

## 아래 내용은 v0.1 원문이며, v0.2 섹션과 충돌하면 v0.2를 우선한다.

작성 기준일: 2026-10-01
대상 독자: 개발자, 코딩 에이전트(Claude Code, Codex), 제안 실무 담당자

이 문서는 무엇을 왜 만드는지에 대한 기준이다. 구현 중 판단이 애매하면 이 문서의 원칙(4장)과 범위(2장)를 우선한다.
작업 단위 지시와 수용 기준은 `docs/PROMPTS.md`에 있다.

---

## 1. 목표

제안서 작성 시간을 크게 줄이면서, 결과물이 AI가 만든 티가 나지 않게 한다.

핵심 아이디어는 다음과 같다.

- 회사가 과거에 잘 쓴(특히 수주한) 제안서 장표를 슬라이드 단위로 쌓아둔다.
- 새 제안서의 특정 장(예: 성과목표)을 쓸 때, 유사 과업의 같은 장 장표를 후보로 보여주고 사람이 고른다.
- 고른 장표는 원본 디자인 그대로 새 파일로 가져오고, 이번 제안서 색상으로 바꾼다.
- 필요하면 AI가 장표 안의 글만 이번 과업에 맞게 바꾼다. 디자인은 AI가 새로 그리지 않는다.
- 이전 사업의 기관명·지역명 등이 남아 있지 않은지 자동으로 검사한다.

전체 흐름은 "공고 탐색 → 사업 카드 → 입찰 서식 채우기 → 제안서 PPT"로 이어지는 파이프라인이다.
앞의 두 단계(공고 탐색, 서식 채우기)는 데모 수준, PPT 단계는 실사용 수준으로 만든다.

## 2. 범위와 단계

| 단계 | 내용 | 수준 | 마일스톤 |
| --- | --- | --- | --- |
| P1 | 장표 라이브러리: 가져오기, 슬라이드 분해, 썸네일, AI 장 구분, 검색, 장바구니, 합치기, 색 바꾸기, 잔존 검사 | 실사용 | M0~M7 |
| P2 | 유사 과업 추천(의미 검색), 별표, AI 글 바꾸기, 구글 드라이브·로그인, 사무실 PC 배포 | 실사용 | M8~M10 |
| P3 | 입찰 서식(HWPX) 채우기 | 데모 | M11 |
| P4 | 나라장터 공고 탐색·추천 | 데모 | M12 |
| 이후 | 항목 수 늘리기/줄이기, 회사 디자인 요소 목록, AI티 판별, 스토리보드 | 미정 | - |

만드는 순서는 파이프라인 순서의 반대다. 실제 가치는 PPT 단계에서 나오므로 그것부터 실사용 수준으로 만들고, 앞단은 나중에 데모로 붙인다.
각 단계는 앞 단계 없이도 사람이 직접 진입할 수 있어야 한다(예: 공고 탐색 없이 사업 카드를 직접 만들어 PPT 단계로 간다).

### 하지 않는 것 (비목표)

- AI가 슬라이드 디자인을 새로 생성하는 기능
- 입찰서 자동 제출, 자동 투찰
- 구형 HWP 파일 자동 변환 (사람이 한글에서 HWPX로 저장해서 올린다)
- 범용 문서 관리 시스템, 사내 위키
- 외부 공개 서비스, 다중 회사(멀티 테넌트) 지원

## 3. 사용자와 대표 시나리오

**제안 실무자 (주 사용자)**
새 공고의 "성과목표" 장을 써야 한다. 사업 카드를 열고 성과목표 장을 고르면, 비슷한 과거 과업의 성과목표 장표들이 썸네일로 뜬다(수주한 것이 위). 하나를 클릭해 장바구니에 담고, 다른 장도 같은 식으로 담는다. 이번 제안서 색상을 고르고 "만들기"를 누르면 하나의 PPTX가 나온다. 장표마다 "그대로 가져오기"와 "글 바꿔서 가져오기"(P2)를 고를 수 있다. 결과와 함께 "이전 사업 이름이 남은 곳" 목록을 받는다. 파워포인트에서 마무리한다.

**아카이브 담당 실무자**
과거 제안서를 사업 폴더 단위로 올리고 사업 정보(분야, 수주 여부 등)를 입력한다. AI가 붙인 장 구분을 확인 화면에서 빠르게 확인·수정한다. 장 구분 목록을 관리한다.

**관리자(개발자)**
설정 파일 관리, AI 사용량·비용 확인, 백업 확인.

## 4. 설계 원칙

1. 디자인은 사람이 만든 원본을 쓴다. AI는 글만 바꾼다.
2. 원본 파일은 수정하지 않는다. 모든 결과는 새 파일이다.
3. 숫자·금액·점수·수주 여부·날짜·인력·실적·기관명은 AI가 생성하지 않는다.
4. AI 라벨은 정해진 목록에서만 고른다.
5. AI 출력은 스키마로 검증하고, 실패하면 사람 확인으로 넘긴다.
6. 모든 AI 호출은 기록한다(모델, 프롬프트 해시, 토큰, 비용, 대상).
7. 사람이 확인하는 지점을 명확히 둔다: 장 구분 확인, 장표 선택, 서식 결과 확인, 최종 PPTX.
8. AI와 구글 연동이 꺼져 있어도 가져오기·검색·합치기·색 바꾸기·잔존 검사는 동작한다.
9. 작업 기록(어떤 장표를 골랐는지, AI 결과를 썼는지, 다운로드 후 시간 등)을 남겨 나중에 개선과 연구에 쓸 수 있게 한다.

## 5. 시스템 구성

```
[Next.js 웹] ──HTTP──> [FastAPI] ──> [PostgreSQL + pgvector]
                           │
                           └──> [Redis] ──> [Celery 작업자]
                                               ├─ LibreOffice + pdftoppm (렌더링)
                                               ├─ python-pptx / lxml (PPTX, HWPX)
                                               ├─ Claude API (core/ai/client.py 경유)
                                               └─ bge-m3 임베딩 (P2)
파일: data/originals (원본, 읽기 전용), data/thumbs, data/outputs
원본 소스: SOURCE=local (data/import 폴더) 또는 SOURCE=gdrive (P2, 구글 드라이브 폴더)
```

### 실행 환경

- 개발: 개발자 PC에서 `docker compose`.
- 실사용: 사무실에 상시 켜둔 PC 한 대(메모리 16GB 이상)에 같은 compose로 배포, 사내망에서 접속.
- 이후 외부 접속이 필요하면 국내 클라우드로 같은 compose를 옮긴다.

### 컨테이너

| 이름 | 내용 |
| --- | --- |
| db | PostgreSQL 16 + pgvector (공식 pgvector 이미지) |
| redis | Redis 7 |
| api | FastAPI (uvicorn) |
| worker | Celery 작업자. LibreOffice, poppler-utils, 한글 폰트 포함. `./fonts`를 `/usr/share/fonts/company`에 마운트 |
| web | Next.js |

### 폰트

회사 제안서에 쓰는 폰트를 `./fonts`에 넣고 worker 컨테이너에 마운트한다(폰트 파일은 저장소에 커밋하지 않는다, 라이선스 확인 필요).
렌더링 전 PPTX에서 사용된 폰트 목록을 뽑아 `fc-list`와 비교하고, 없는 폰트는 경고로 기록한다. 폰트가 없으면 썸네일이 실제와 다르게 보인다.

## 6. 데이터 모델

모든 테이블에 `id`(UUID), `created_at`, `updated_at`을 둔다. 아래는 그 외 필드다.

### 6.1 사업 카드와 문서

```
projects                  -- 사업 카드. 과거 사업과 진행 중인 입찰을 같은 테이블로 관리
  name                    사업명
  agency                  발주 기관
  parent_agency           상위 기관/부처 (선택)
  domain                  사업 분야 (config/labels.yaml의 domains 중 하나)
  region                  지역 (선택)
  year                    연도
  amount_krw              사업 금액 (정수, 선택)
  stage                   archived | exploring | preparing | submitted | won | lost
  won                     수주 여부 (true/false/null)
  tech_score, tech_rank   기술평가 점수·순위 (선택, 사람 입력)
  notice_no               공고번호 (선택)
  palette_key             이번 제안서 색상 (config/palettes.yaml 키, 진행 중 사업용)
  source                  local | gdrive | notice
  source_ref              드라이브 폴더 ID 등
  task_summary            jsonb, 과업 요약 (P2)
  task_embedding          vector(1024), 과업 요약 임베딩 (P2)
  notes

documents
  project_id
  kind                    proposal_pptx | notice | task_spec | scoring_table | form_hwpx | other
  filename                원래 파일명
  stored_path             data/originals/<sha256>.<ext>
  sha256                  중복 방지
  source_ref              드라이브 파일 ID 등
  source_modified_at
  status                  pending | processing | ready | failed
  error
  fonts_used              jsonb, 문서에서 쓰인 폰트 목록
  fonts_missing           jsonb
```

### 6.2 슬라이드와 라벨

```
slides
  document_id
  slide_index             1부터
  title                   제목 (휴리스틱으로 추출)
  text                    전체 텍스트 (도형 읽는 순서대로)
  tables_md               표를 마크다운으로
  notes                   발표자 노트
  shapes                  jsonb: [{shape_id, name, kind, x, y, w, h, text, char_count}]
  thumb_path              썸네일 (가로 480px)
  preview_path            크게 보기 (가로 1600px)
  description             AI 한 줄 설명 (최대 60자)
  chapter_key             장 구분 (labels.yaml chapters 키 또는 unknown)
  chapter_confidence      0~1
  chapter_source          ai | human
  chapter_confirmed       사람 확인 여부
  stats                   jsonb: {char_count, shape_count, has_table, has_chart, has_picture, raster_ratio}
  colors                  jsonb: 사용된 색과 면적 가중치
  embedding               vector(1024), P2
  star_count              캐시

slide_label_events        -- 라벨 변경 이력
  slide_id, field, old_value, new_value, source (ai|human), confidence, user_email

slide_stars
  slide_id, user_email
```

### 6.3 새 제안서(덱) 만들기

```
decks
  project_id              진행 중인 사업 카드
  title
  palette_key
  status                  draft | building | ready | failed
  output_path             data/outputs/<deck_id>.pptx
  report                  jsonb: 잔존 검사 결과, 경고, 색 변경 불가 장표 등

deck_items
  deck_id
  position                순서
  chapter_key
  source_slide_id
  mode                    as_is | rewrite
  rewrite_result          jsonb: {shape_id: new_text}, P2
  rewrite_status          none | pending | done | failed
```

### 6.4 작업, AI 기록, 사용 기록

```
jobs
  kind, target_type, target_id, status (queued|running|done|failed), progress, error, started_at, finished_at

ai_calls
  purpose                 chapter_segment | slide_describe | rewrite | form_map | notice_summary ...
  model
  prompt_name, prompt_hash
  input_tokens, output_tokens, cost_usd (config/pricing.yaml로 계산)
  target_type, target_id
  latency_ms, status, error

usage_events              -- 연구·개선용 기록
  user_email, event (search|view_slide|add_to_cart|build_deck|download|choose_mode ...), payload jsonb
```

### 6.5 회사 데이터 (P3)

```
company_profile           회사 일반 현황 (단일 행)
personnel                 참여 가능 인력 (이름, 직급, 학력, 자격 등)
personnel_careers         인력별 경력 (기간, 기관, 사업명, 역할)
track_records             수행 실적 (사업명, 발주 기관, 기간, 금액, 분야)
```

### 6.6 공고 (P4)

```
notices                   나라장터 공고 원본 필드 + 점수 + AI 요약 + 상태(new|ignored|carded)
```

## 7. 설정 파일

### config/labels.yaml

```yaml
version: 1
chapters:              # 공공 용역 제안서 기준 장 구분. 실무자가 다듬는다.
  - {key: cover,        name: 표지}
  - {key: toc,          name: 목차}
  - {key: divider,      name: 간지}
  - {key: overview,     name: 제안 개요·일반 현황}
  - {key: understanding,name: 사업 이해(배경·목적·현황 분석)}
  - {key: strategy,     name: 추진 전략(목표·전략·차별화)}
  - {key: kpi,          name: 성과목표}
  - {key: method,       name: 세부 수행 방법}
  - {key: organization, name: 추진 체계(조직·인력)}
  - {key: schedule,     name: 추진 일정}
  - {key: quality,      name: 품질·보안·위험 관리}
  - {key: management,   name: 사업 관리(보고·협의)}
  - {key: effect,       name: 기대효과·활용 방안}
  - {key: company,      name: 회사 소개·수행 실적}
  - {key: appendix,     name: 부록}
domains:               # 사업 분야. 실무자가 다듬는다.
  - {key: tourism, name: 관광}
  - {key: culture, name: 문화}
  - {key: policy,  name: 정책 연구}
  - {key: survey,  name: 실태 조사}
  - {key: other,   name: 기타}
```

라벨 목록이 바뀌면 `version`을 올린다. 기존 라벨은 지우지 않고 `deprecated: true`로 표시한다.

### config/palettes.yaml

```yaml
default: intwin
palettes:
  intwin:  {primary: "#1F4E79", secondary: "#5B9BD5", accent: "#C55A11", neutral: "#7F7F7F"}
```

실제 회사 색으로 교체한다. 사업 카드마다 팔레트를 고를 수 있다.

### config/banned_phrases.yaml (P2)

AI 글 바꾸기 결과에서 피할 표현 목록. 예: "극대화", "시너지", "혁신적인", "~를 통해 ~를 도모".

### config/pricing.yaml

모델별 입력·출력 토큰 단가(USD). 값은 Anthropic 공식 가격 페이지를 보고 사람이 채운다. 코드에 가격을 박지 않는다.

### config/notice_rules.yaml (P4)

공고 추천 규칙(포함·제외 키워드, 업종, 금액 범위, 지역, 최소 남은 일수, 가중치).

## 8. 처리 흐름 상세

### 8.1 가져오기 (M1, 드라이브는 M10)

- `SOURCE=local`: `data/import/` 아래 사업 폴더 단위로 읽는다. 폴더 하나가 사업 하나다.
- 사업 정보는 `data/import/projects.csv`(구글 시트에서 내보낸 것)로 받는다. 열: `folder, name, agency, parent_agency, domain, region, year, amount_krw, won, tech_score, tech_rank, notes`.
- 파일 종류는 파일명 규칙으로 추정하고(`제안서`, `공고`, `과업지시서`, `배점`, `서식`) 화면에서 고칠 수 있게 한다.
- 원본은 `data/originals/<sha256>.<ext>`로 복사하고 읽기 전용 권한을 준다. 같은 해시면 다시 처리하지 않는다.
- `SOURCE=gdrive`(M10): 서비스 계정으로 지정 폴더를 재귀 조회. 파일 ID와 수정 시각으로 변경을 감지한다. 사업 정보는 구글 시트에서 읽는다.

### 8.2 PPTX 분해 (M1)

슬라이드마다 다음을 뽑는다.

- 제목: 제목 placeholder가 있으면 그것, 없으면 상단 20% 영역에서 글자 크기가 가장 큰 텍스트.
- 텍스트: 도형을 위→아래, 왼쪽→오른쪽 순서로 읽어 이어 붙인다. 그룹 도형은 재귀로 들어간다.
- 표: 마크다운으로 변환해 `tables_md`에 둔다.
- 도형 목록: shape_id, 이름, 종류, 위치·크기(EMU), 텍스트, 글자 수. 글 바꾸기(P2)의 기준이 된다.
- 통계: 글자 수, 도형 수, 표·차트·그림 포함 여부, 그림(래스터)이 차지하는 면적 비율.
- 색: 도형 채우기·선·글자 색을 `srgbClr`와 테마 색(`schemeClr`, 소스 테마로 해석)으로 모으고 면적 가중치를 기록. `lumMod`, `lumOff`, `tint`, `shade` 변형을 반영한다.
- 사용 폰트: 텍스트 run의 latin/ea 폰트와 테마 폰트.

### 8.3 렌더링 (M1)

- `soffice --headless --convert-to pdf`로 PDF를 만들고 `pdftoppm`으로 슬라이드별 PNG를 만든다.
- 썸네일 가로 480px, 크게 보기 가로 1600px.
- 렌더링은 원본이 아니라 원본 복사본을 임시 폴더에서 처리한다.
- 목표 성능: 80장짜리 PPTX를 4코어 PC에서 추출+렌더링 2분 이내.

### 8.4 AI 장 구분과 설명 (M3)

1. 덱 단위 장 구분: 슬라이드 번호와 제목 목록, 목차로 보이는 슬라이드의 이미지를 주고, 각 슬라이드의 `chapter_key`와 확신도를 받는다. 장은 연속 구간이라는 점을 프롬프트에 명시하고, 결과도 코드에서 후처리(짧게 끊긴 구간 보정)한다.
2. 슬라이드 설명: 썸네일 이미지와 텍스트를 주고 60자 이내 한 줄 설명을 받는다. 설명에는 기관명·지역명·수치를 넣지 않게 한다(검색용 일반 설명).
3. 결과는 `chapter_source=ai`, `chapter_confirmed=false`로 저장하고 확인 화면 대기열에 넣는다.
4. 대량 처리 시 가벼운 모델을 쓰고, 처음 10건은 사람 정답과 비교해 정확도를 기록한다(`evals/`).

### 8.5 검색 (M2, 의미 검색은 M8)

- P1: 필터(분야, 연도, 수주 여부, 기관, 장) + 키워드(제목·텍스트·설명 대상, 대소문자 무시 부분 일치). 수천~수만 장 규모에서는 이것으로 충분하다.
- 정렬 기본값: 수주 여부(수주 우선) → 별표 수 → 연도 최신순.
- P2: bge-m3 임베딩(제목+설명+텍스트)으로 의미 검색을 추가하고, 키워드 결과와 RRF(reciprocal rank fusion)로 합친다.

### 8.6 슬라이드 합치기 (M4) — 가장 어려운 부분

여러 원본 PPTX에서 고른 슬라이드를 하나의 새 PPTX로 합친다. 원본과 똑같이 보여야 한다.

어려운 이유: 슬라이드는 레이아웃·마스터·테마를 상속받고, 그림·차트·임베디드 객체를 관계(rId)로 참조한다. 원본마다 마스터가 다르다.

구현 방식은 `core/pptx/merge.py`에 `SlideMerger` 인터페이스를 두고 백엔드를 바꿔 끼울 수 있게 한다.

- `python` 백엔드(기본): 새 덱에 빈 레이아웃 슬라이드를 만들고, 원본 슬라이드의 도형 트리와 배경을 복사한다. 그림·차트·미디어 파트를 새 패키지로 복사하고 rId를 다시 연결한다. placeholder가 레이아웃에서 상속받던 위치·서식과 테마 색·폰트는 복사 시점에 명시적인 값으로 "굳혀서" 새 마스터에서도 같게 보이게 한다.
- `aspose` 백엔드(선택): 상용 라이브러리 Aspose.Slides의 슬라이드 복제 기능.
- `powerpoint` 백엔드(선택): 파워포인트가 설치된 윈도우 PC에서 자동화로 슬라이드 삽입.

M4는 먼저 1~2일짜리 스파이크로 세 방식을 가짜 덱 5종(그룹 도형, 표, 차트, 그림, placeholder 상속, 서로 다른 테마 포함)에 시험하고, 결과(시각 비교 점수, 파워포인트에서 복구 경고 없이 열리는지, 구현 비용)를 보고한 뒤 선택한다.

수용 기준: 합친 결과의 각 슬라이드를 렌더링해 원본 썸네일과 비교했을 때 SSIM 0.95 이상, 파워포인트와 LibreOffice에서 복구 경고 없이 열림.

### 8.7 색 바꾸기 (M6)

- 슬라이드에서 쓰인 유채색을 면적 가중치로 모으고, 비슷한 색(ΔE 10 미만)을 묶는다. 흰색에 가까운 색, 검정에 가까운 색, 채도가 낮은 회색은 기본적으로 건드리지 않는다.
- 가장 많이 쓰인 묶음 → primary, 두 번째 → secondary, 면적은 작지만 채도가 높은 묶음 → accent로 대응시킨다.
- 같은 묶음 안의 밝고 어두운 변형은 원래 색과의 밝기 차이를 유지하며 대상 색에 적용한다.
- 테마 색 참조는 해석한 뒤 명시 색으로 바꿔 적용한다.
- 그림(래스터) 안의 색은 바꿀 수 없다. 그림 면적 비율이 높은 장표는 리포트에 "색 변경이 일부만 적용됨"으로 표시한다.
- 사람이 대응 관계를 바꿀 수 있게 결과 미리보기에서 묶음별 대상 색을 고칠 수 있다.

### 8.8 잔존 검사 (M7)

- 기준 목록: 원본 사업의 기관명, 상위 기관, 사업명, 지역명(기관명에서 "OO시", "OO군", "OO도" 등의 지명 추출), 연도 표기. P2부터 AI가 원본 문서에서 뽑은 고유명사를 추가한다.
- 새 사업 카드에도 같은 값이 있으면(같은 기관 재입찰 등) 제외한다.
- 결과 덱의 모든 텍스트(표, 그룹 도형 포함, 노트 선택)를 검사해 슬라이드·도형별로 리포트한다.
- 화면에서 해당 장표에 경고 표시를 하고, 다운로드 시 리포트를 함께 준다.

### 8.9 유사 과업 추천 (M8)

- 새 사업 카드에 과업지시서(HWPX 또는 PDF)를 올리면 AI가 과업 요약(주요 과업 항목, 대상 지역, 분야)을 만들고 임베딩한다.
- 과거 사업 카드들의 과업 요약 임베딩과 비교해 비슷한 사업을 찾는다. 과거 사업에 과업지시서가 없으면 제안서 앞부분(사업 이해 장) 텍스트로 대신한다.
- 장을 고르면 후보 장표 정렬 점수 = 유사도 + 수주 가산 + 별표 가산 + 최신 가산(가중치는 설정 파일).

### 8.10 AI 글 바꾸기 (M9)

- 입력: 원본 슬라이드의 도형별 텍스트(shape_id, 역할 추정, 글자 수), 새 사업 카드 정보, 과업 요약, 금지 표현 목록.
- 출력: `{shape_id: new_text}`. 각 도형의 글자 수는 원래 글자 수의 85~115% 범위.
- 규칙: 원본에 있던 수치·금액·날짜는 새 사업 카드에 근거가 없으면 `[확인 필요]`로 바꾼다. 기관명·지역명은 새 사업 카드 값만 쓴다.
- 적용: 문단 단위로 첫 run의 서식을 유지하고 텍스트만 교체한다. 문단 수가 달라지면 마지막 문단 서식을 복제한다.
- 적용 후 잔존 검사와 금지 표현 검사를 다시 돌린다.
- 사람은 장표별로 "그대로 가져오기 / 글 바꿔서 가져오기"를 고르고, 바꾼 글을 화면에서 확인·수정한 뒤 만든다.

### 8.11 입찰 서식 채우기 (M11, 데모)

- 입력은 사람이 한글에서 HWPX로 저장한 서식 파일.
- HWPX는 zip 안의 XML이다. `Contents/section*.xml`에서 표(`hp:tbl`), 행, 셀, 문단, 텍스트를 읽어 셀 좌표가 붙은 격자 JSON으로 만든다.
- AI는 "어느 셀이 어떤 회사 데이터 항목인지"만 대응시킨다(예: 셀(2,3) → `personnel.name`). 값은 코드가 DB에서 채운다. 인력·실적이 여러 명/건이면 행을 복제한다.
- 사람이 화면에서 대응 관계를 확인한 뒤 채운다.
- 다시 압축할 때 원본 zip의 파일 순서와 각 파일의 압축 방식을 그대로 유지한다.
- 데모 범위: 일반 현황, 참여 인력, 수행 실적 서식 세 종류.

### 8.12 공고 탐색·추천 (M12, 데모)

- 공공데이터포털의 조달청 나라장터 입찰공고정보서비스(용역 공고 조회)를 쓴다. 인증키는 `.env`. 정확한 엔드포인트와 파라미터는 공공데이터포털 문서를 확인해서 구현한다.
- `notice_rules.yaml` 규칙으로 점수를 매기고, 상위 N건만 AI가 3줄 요약한다.
- "사업 카드 만들기"를 누르면 `projects`에 `stage=exploring`으로 생성되고 이후 단계로 이어진다.
- 첨부 문서를 API로 받을 수 있는지 먼저 확인하고, 안 되면 사람이 내려받아 올리는 흐름으로 대신한다.

## 9. 화면

| 경로 | 내용 | 마일스톤 |
| --- | --- | --- |
| `/` | 대시보드: 진행 중 사업 카드, 최근 작업 상태 | M2 |
| `/projects` | 사업 카드 목록·필터, 새 카드 만들기 | M2 |
| `/projects/[id]` | 카드 상세: 정보 편집, 문서 목록·올리기, 처리 상태, 덱 목록 | M2 |
| `/library` | 장표 라이브러리: 왼쪽 필터, 위 검색창, 썸네일 그리드, 클릭 시 크게 보기·원본 정보·별표·바구니 담기 | M2 |
| `/review` | 장 구분 확인 대기열: 확신도 낮은 순, Enter 확인, 숫자 키로 장 선택, 덱 단위 일괄 확인 | M3 |
| `/decks/[id]` | 덱 빌더: 장 순서 편집, 장별 후보 장표, 바구니, 장표별 모드 선택, 팔레트, 만들기, 리포트, 다운로드 | M5 |
| `/forms` | 서식 채우기 데모 | M11 |
| `/company` | 회사 데이터(인력, 실적) 입력 | M11 |
| `/notices` | 공고 탐색 데모 | M12 |
| `/settings` | 장 목록, 분야, 팔레트, 금지 표현 보기·편집, AI 사용량·비용 | M3~ |

화면 원칙: 실무자가 엑셀·노션 수준으로 쓸 수 있게 단순하게. 썸네일이 주인공이다. 처리 중인 작업은 진행 상태를 보여준다.

## 10. AI 사용 규칙

- 모델은 설정으로 바꿀 수 있게 하고 기본값은 다음과 같다.
  - 장 구분, 슬라이드 설명, 서식 대응, 공고 요약: `claude-haiku-4-5-20251001`
  - 글 바꾸기, 과업 요약: `claude-sonnet-5-5`
- 모델 이름, 가격, API 기능은 바뀔 수 있으므로 구현 전에 Anthropic 공식 문서(https://docs.claude.com)를 확인한다.
- 프롬프트는 `prompts/<name>.md`에 두고, 실행 시 내용 해시를 `ai_calls.prompt_hash`에 기록한다.
- 모든 응답은 Pydantic 스키마로 검증한다. 형식 오류는 최대 2회 재시도, 이후 `failed`로 두고 사람 확인으로 넘긴다.
- 이미지 입력은 썸네일(가로 1600px 이하)을 쓴다.
- 과거 자료 대량 처리는 대기열로 천천히 돌리고, 공식 문서에서 배치 처리 기능을 확인해 비용을 줄인다.
- `AI_ENABLED=false`면 AI 단계는 건너뛰고 해당 필드는 비워둔다. 테스트는 mock 응답을 쓴다.
- AI에 보내는 자료에 대해서는 진행 중 과업 계약서의 외부 전송 제한 조항을 사람이 먼저 확인한다(13장).

## 11. 비기능 요구사항

- **접속**: P1은 사내망 전용. M10부터 구글 계정 로그인(회사 도메인만 허용).
- **권한**: P1은 모든 사용자 동일 권한. 설정 편집과 라벨 목록 변경은 관리자 이메일 목록(`.env`)만.
- **백업**: 매일 `pg_dump`를 `data/backups/`에 저장하고 7일치 보관. M10에서 구글 드라이브 업로드 추가. `data/originals`는 원본이 드라이브에 있으므로 백업 대상에서 선택.
- **로그**: API·작업자 로그는 JSON 형식, 작업 실패는 `jobs.error`에 사람이 읽을 수 있는 문장으로.
- **성능**: 라이브러리 검색 응답 1초 이내(슬라이드 5만 장 기준), 덱 만들기 30장 기준 1분 이내.
- **재현성**: 같은 원본과 같은 설정으로 다시 처리하면 같은 추출 결과가 나와야 한다(AI 단계 제외).

## 12. 테스트와 품질 기준

- `core/`는 단위 테스트 필수. PPTX·HWPX 테스트 문서는 테스트 코드가 직접 생성한다.
- 합치기·색 바꾸기는 렌더링 이미지 비교 테스트(SSIM)를 둔다.
- AI 관련 품질은 `evals/`에 사람 정답 데이터를 두고 스크립트로 정확도를 계산한다. 프롬프트나 모델을 바꿀 때마다 돌린다.
  - 장 구분 정확도(슬라이드 단위 일치율)
  - 글 바꾸기: 글자 수 범위 준수율, 잔존 고유명사 0건 비율, 금지 표현 0건 비율
- 실사용 지표(usage_events로 계산): 덱 하나 만드는 데 걸린 시간, 장표별 모드 선택 비율, 글 바꾸기 결과를 사람이 고친 정도(가능하면 다운로드한 파일을 다시 올려 비교).

## 13. 열려 있는 결정 사항

| 항목 | 선택지 | 기본안 |
| --- | --- | --- |
| 실사용 서버 위치 | 사무실 상시 PC / 국내 클라우드 | 사무실 상시 PC로 시작 |
| 슬라이드 합치기 방식 | python 직접 구현 / Aspose.Slides / 파워포인트 자동화 | M4 스파이크 결과로 결정 |
| AI로 보내는 자료 범위 | 과업 계약서 외부 전송 조항 확인 필요 | 확인 전에는 과거 자료만 처리 |
| 폰트 라이선스 | 서버 설치 가능 여부 확인 | 확인 후 `./fonts` 마운트 |
| 나라장터 첨부 문서 | API 제공 범위 확인 | 안 되면 수동 업로드 |
| 사업 분야·장 목록 | 실무자 확정 필요 | 7장 초안으로 시작 |

## 14. 용어

- **사업 카드**: 사업 하나(과거 사업 또는 진행 중인 입찰)에 대한 정보와 문서를 묶은 단위. `projects` 테이블.
- **장**: 제안서의 큰 구분(사업 이해, 추진 전략, 성과목표 등). `chapter_key`.
- **장표**: 슬라이드 한 장.
- **덱**: 새로 만드는 제안서 PPTX 하나. 여러 원본에서 고른 장표의 묶음.
- **잔존 검사**: 이전 사업의 기관명·지역명 등이 결과물에 남아 있는지 찾는 검사.
- **그대로 가져오기 / 글 바꿔서 가져오기**: 장표를 원본 글 그대로 넣을지, AI가 글을 바꿔서 넣을지의 선택.
