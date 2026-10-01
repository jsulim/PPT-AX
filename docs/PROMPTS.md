# 코딩 에이전트 작업 지시서 (M0~M12)

## v0.2 현재 유효한 작업 순서

아래 v0.2 마일스톤이 현재 유효하다. 이 섹션과 아래 기존 v0.1 마일스톤이 충돌하면 v0.2를 우선한다.
M0은 이미 저장소 뼈대와 실행 환경으로 유지한다.

---

## M1. 템플릿 PPTX 등록과 텍스트 슬롯 추출

```text
AGENTS.md와 docs/PROJECT_SPEC.md의 0장(v0.2 방향 전환), 5장(시스템 구성), 6장(데이터 모델)을 읽고 M1을 진행해줘. 계획 먼저 보여줘.

목표: 기존 제안서 PPTX를 템플릿으로 등록하고, 교체 가능한 텍스트 슬롯을 추출한다. 템플릿은 완성 제안서 한 벌이 아니라 장표 유형 모음으로 다룬다. 디자인·아이콘·도형·레이아웃은 건드리지 않는다.

할 일:
1. DB: projects, documents, templates, template_text_slots, outlines 테이블과 마이그레이션.
2. core/pptx/slots.py:
   - PPTX 경로를 받아 슬라이드별 텍스트 슬롯을 데이터 객체로 반환.
   - 슬롯에는 slide_index, shape_id, kind(text_box/table_cell/placeholder/notes), original_text, char_count, max_char_count, bounds, style_ref, locked 후보를 포함.
   - 슬롯 유형은 fact/narrative/fixed/unknown 후보로 둔다. page number, footer, 로고성 짧은 텍스트는 fixed 또는 locked 후보로 표시한다.
   - 그룹 도형은 재귀로 읽고, 표 셀 텍스트도 슬롯으로 뽑는다.
   - 자동 추출은 이름 붙이기 보조일 뿐이다. 사람이 템플릿당 한 번 slot_project_name 같은 slot_name, role_key, value_type, field_binding을 확정할 수 있어야 한다.
   - DB에 의존하지 않는다.
3. core/pptx/render.py:
   - 템플릿 복사본을 임시 폴더에서 PDF/PNG로 렌더링한다.
   - 썸네일 가로 480px, 크게 보기 가로 1600px.
4. core/pptx/fonts.py: 사용 폰트 목록과 설치 여부 비교.
5. worker 작업: analyze_template(document_id) -> 슬롯 추출, 렌더링, 폰트 기록.
6. API: 템플릿 업로드, 템플릿 목록, 템플릿 상세, 슬롯 목록/수정, 미리보기 이미지 제공.
7. 테스트: python-pptx로 가짜 템플릿을 만들고 텍스트 박스, 표, 그룹 도형, placeholder 텍스트가 슬롯으로 추출되는지 검증.

수용 기준:
- 가짜 PPTX 템플릿 3개를 업로드하면 templates와 template_text_slots가 생성된다.
- 원본 PPTX는 data/originals/<sha256>.pptx에 저장되고 수정되지 않는다.
- 표 셀과 그룹 도형 안의 텍스트도 슬롯으로 잡힌다.
- 슬롯별 original_text, char_count, max_char_count가 저장된다.
- 사람이 slot_name, role_key, value_type, field_binding, locked를 수정할 수 있다.
- 템플릿 썸네일 파일이 생성된다.
- 회사 폰트가 없으면 fonts_missing에 기록된다.

하지 말 것: AI 글 생성, 장표 라이브러리, 여러 PPT 합치기.
```

---

## M2. 사업 카드, 공고/과업 입력, 입찰정보 입력 화면

```text
docs/PROJECT_SPEC.md의 v0.2 MVP 흐름과 데이터 모델을 읽고 M2를 진행해줘. 계획 먼저.

목표: 사용자가 새 사업 카드, 공고/과업 자료, 입찰정보를 입력하고 템플릿을 선택할 수 있게 한다.

할 일:
1. DB: notice_contexts, bid_contexts, usage_events 테이블과 마이그레이션.
2. API:
   - 사업 카드 생성·수정.
   - 공고문/과업지시서 텍스트 저장. notice_contexts에는 자유 요약보다 requirements(번호, 요구사항, 출처 쪽수, 배점 항목)와 scoring_items를 우선 저장한다.
   - 입찰정보 JSON 저장/수정. 회사 일반 현황, 참여 인력, 수행 실적, 기타 확정 정보 구조를 받는다.
   - 프로젝트에 템플릿 연결.
   - outline 초안 저장/수정. M2에서는 사람이 배점표 항목 → 장표 유형 → 장 수를 직접 입력한다.
3. web:
   - /projects 목록과 새 카드 만들기.
   - /projects/[id] 상세.
   - /projects/[id]/inputs: 공고문·과업지시서 붙여넣기/파일 등록, 요구사항 목록 확인, 입찰정보 입력, 템플릿 선택, outline 입력.
   - /templates: 템플릿 목록과 미리보기.
4. usage_events: create_project, upload_notice, edit_bid_context, choose_template 기록.

수용 기준:
- 사업 카드 생성 -> 공고문 텍스트/요구사항 입력 -> 입찰정보 입력 -> 템플릿 선택 -> outline 입력까지 화면에서 가능하다.
- 입력한 공고/입찰정보가 다시 열었을 때 유지된다.
- 처리 실패 시 사람이 읽을 수 있는 한 문장 오류가 보인다.

하지 말 것: AI 요약, AI 글 바꾸기.
```

---

## M3. 공고/과업 요구사항 구조화와 텍스트 슬롯 역할 제안

```text
docs/PROJECT_SPEC.md의 4장 원칙, 8.2, 8.5, 10장을 읽고 M3을 진행해줘. 계획 먼저.

목표: AI가 공고/과업 내용을 요구사항 목록으로 구조화하고, 템플릿 텍스트 슬롯의 역할·유형·필드 연결 후보를 제안한다. 값은 만들지 않는다.

할 일:
1. core/ai/client.py:
   - anthropic SDK 래퍼.
   - 모델·최대 토큰은 설정에서, 프롬프트는 prompts/<name>.md를 읽어 변수 치환, 내용 해시 계산.
   - 응답을 Pydantic 모델로 검증, 형식 오류 시 최대 2회 재시도.
   - ai_calls 테이블에 모델, prompt_name, prompt_hash, 토큰, 비용, 대상, 지연, 상태 기록.
   - AI_ENABLED=false면 호출하지 않고 None 반환. 테스트용 mock 모드.
2. prompts/notice_requirements.md:
   - 공고/과업 원문 + 배점표 -> requirements[{req_id, title, detail, source_page, source_text, scoring_item_key}], scoring_items.
   - 원문에 없는 금액, 날짜, 기관명은 만들지 않는다.
3. prompts/slot_role.md:
   - 슬롯 원문, 위치, 슬라이드 번호, 원래 글자 수 -> role_key, value_type(fact/narrative/fixed/unknown), field_binding 후보 제안.
   - fact 슬롯은 값 자체가 아니라 bid_context/project_card/DB의 JSON 경로만 제안한다.
   - 목록 밖은 unknown.
4. worker 작업: structure_notice_requirements(project_id), classify_template_slots(template_id).
5. web:
   - 요구사항 목록과 배점 항목 확인/수정.
   - 슬롯 역할, 유형, 필드 연결 확인/수정.

수용 기준:
- mock 응답으로 요구사항 구조화와 슬롯 역할/유형/필드 연결 제안 전체 흐름이 돈다.
- 모든 AI 호출이 ai_calls에 기록된다.
- 목록 밖 role_key는 unknown으로 저장된다.
- AI_ENABLED=false면 요구사항/역할/필드 연결 제안 없이 사람 입력으로 진행 가능하다.

하지 말 것: 최종 PPTX 생성, 텍스트 교체 적용.
```

---

## M4. AI 텍스트 교체안 생성과 검증

```text
docs/PROJECT_SPEC.md의 8.5, 8.6, 10, 12장을 읽고 M4를 진행해줘. 계획 먼저.

목표: 공고/과업 요구사항, 사업 카드, 입찰정보, 템플릿 원문을 근거로 텍스트 슬롯별 교체안을 만든다. 사실 슬롯은 코드가 값을 채우고, AI는 서술 슬롯만 문장을 쓴다.

할 일:
1. DB: generated_decks, deck_text_rewrites.
2. prompts/rewrite_slots.md:
   - 입력: narrative 슬롯 원문, 슬롯 역할, 원래 글자 수/max_char_count, 요구사항 목록, 사업 카드, 입찰정보, 금지 표현.
   - 출력: {slot_id, suggested_text, requirement_ids, warnings}.
   - 원문 대비 글자 수 기본 70~130%, max_char_count를 넘지 않는 것을 우선한다.
   - 근거 없는 숫자·날짜·금액·인력·실적은 만들지 않고 [확인 필요]로 둔다.
   - fact 슬롯은 프롬프트 입력에서 제외하거나 field_binding만 전달한다. fact 슬롯 값은 코드가 JSON에서 그대로 채운다.
3. core/pptx/rewrite_plan.py:
   - AI 결과 검증. 새 숫자·날짜·고유명사 탐지, 요구사항 출처 연결, 금지 표현, 잔존 용어, 글자 수 범위.
   - 서술 슬롯에 등장한 숫자, 날짜, 고유명사가 공고/과업 요구사항, project_card, bid_context, 회사 DB 중 하나에 실제로 있는지 검사한다.
   - fact 슬롯은 field_binding을 따라 값을 치환하고, AI suggested_text가 들어오면 거부한다.
   - 경고 목록 생성.
4. API/worker: generate_rewrite(deck_id).
5. web /decks/[id]/rewrite:
   - 원문과 교체안을 나란히 표시.
   - 슬롯별 수락, 수정, 원문 유지, 교체 제외.
   - 경고 표시.
6. evals/rewrite 기본 스크립트: 글자 수 준수율, 경고 개수 계산.

수용 기준:
- mock 응답으로 슬롯별 교체안이 생성되고 사람이 수정/확정할 수 있다.
- 사실 슬롯은 bid_context/project_card 값이 그대로 들어가고 AI가 바꾼 값은 거부된다.
- 원본 입력에 없던 숫자·날짜·고유명사가 생기면 경고한다.
- 요구사항과 연결되지 않은 장표/슬롯이 보이면 경고한다.
- 금지 표현이 있으면 경고한다.
- [확인 필요]가 화면에 보인다.

하지 말 것: PPTX 파일에 아직 적용하지 않는다.
```

---

## M5. PPTX 복사본 생성과 텍스트 적용

```text
docs/PROJECT_SPEC.md의 8.7, 8.8을 읽고 M5를 진행해줘. 계획 먼저.

목표: 원본 템플릿 PPTX 복사본에 확정된 텍스트만 적용해 새 PPTX를 만든다.

할 일:
1. core/pptx/apply_text.py:
   - 템플릿 PPTX 경로, 슬롯별 final_text를 받아 새 PPTX를 data/outputs에 저장.
   - fact 슬롯은 field_binding으로 JSON 값을 그대로 읽어 치환한다.
   - narrative 슬롯은 사람이 확정한 final_text만 적용한다.
   - 문단 첫 run의 서식을 유지하고 텍스트만 교체.
   - 표 셀 텍스트도 교체.
   - 교체 제외 슬롯은 건드리지 않음.
   - 원본 파일은 절대 수정하지 않음.
2. worker 작업: build_generated_deck(deck_id).
3. 잔존 검사:
   - 템플릿 원문의 기관명/사업명/지역명 후보와 새 사업 카드 값을 비교.
   - 결과 PPTX의 모든 텍스트를 검사.
   - 서술 슬롯 안의 숫자·날짜·고유명사가 입력 근거에 있는지 다시 검사.
4. web /decks/[id]:
   - 생성 진행 상태, 경고 리포트, 다운로드.
5. 테스트:
   - 가짜 템플릿에 텍스트 적용 후 다시 열어 값이 바뀌었는지 확인.
   - 원본 파일 해시가 변하지 않는지 확인.

수용 기준:
- 확정한 텍스트가 결과 PPTX에 적용된다.
- fact 슬롯은 JSON 값과 완전히 같은 문자열로 적용된다.
- 원본 PPTX 해시가 변하지 않는다.
- 표 셀과 그룹 도형 안 텍스트도 적용된다.
- 잔존 기관명 리포트가 생성된다.

하지 말 것: 레이아웃 변경, 아이콘 생성, 색 변경.
```

---

## M6. 생성 품질 확인과 렌더링 미리보기

```text
docs/PROJECT_SPEC.md의 8.8, 11, 12장을 읽고 M6을 진행해줘. 계획 먼저.

목표: 생성된 PPTX를 렌더링해 사람이 확인하고, 글자 수/잔존/폰트 경고를 리포트한다.

할 일:
1. 결과 PPTX 렌더링: 썸네일 480px, 크게 보기 1600px.
2. 간이 overflow 검사: 텍스트 길이와 원래 슬롯 크기를 기준으로 위험 슬롯 표시.
3. 리포트 강화: [확인 필요], 새 숫자 의심, 금지 표현, 잔존 용어, 폰트 누락.
4. web: 결과 미리보기, 슬라이드별 경고, 리포트 다운로드.

수용 기준:
- 결과 PPTX 미리보기가 화면에 표시된다.
- 경고가 있는 슬롯/슬라이드가 구분되어 보인다.
- 리포트 텍스트 파일을 받을 수 있다.
```

---

## M7. P1 사용 흐름 완성

```text
docs/PROJECT_SPEC.md의 v0.2 MVP 흐름 전체를 읽고 M7을 진행해줘. 계획 먼저.

목표: 공고/입찰정보/템플릿 선택부터 PPTX 다운로드까지 한 흐름으로 다듬는다.

할 일:
1. 대시보드와 프로젝트 상세에서 다음 해야 할 일을 보여준다.
2. 각 단계 상태(project, inputs, template, rewrite, build)를 명확히 표시한다.
3. 실패 작업 재시도 버튼.
4. AI_ENABLED=false에서도 템플릿 분석, 수동 텍스트 입력, PPTX 생성, 잔존 검사가 동작하게 한다.
5. usage_events 주요 이벤트 기록.

수용 기준:
- 새 사업 카드 생성 -> 공고/입찰정보 입력 -> 템플릿 선택 -> 텍스트 교체안 확인 -> PPTX 생성 -> 다운로드가 화면에서 끝까지 된다.
- AI_ENABLED=false에서 수동 입력으로 결과 PPTX를 만들 수 있다.
- 실패 작업은 한 문장 오류와 재시도 버튼을 제공한다.
```

---

## M8. 회사 데이터와 HWPX 서식 읽기

```text
docs/PROJECT_SPEC.md의 6.5, 8.9를 읽고 M8을 진행해줘. 계획 먼저.

목표: 회사 일반 현황, 참여 인력, 수행 실적을 관리하고 HWPX 서식에서 표 구조를 읽는다.

할 일:
1. DB: company_profile, personnel, personnel_careers, track_records.
2. /company 입력 화면. 엑셀 붙여넣기 지원은 가능하면 구현.
3. core/hwpx/read.py: HWPX zip 내부 XML에서 표, 행, 셀, 문단, 텍스트를 격자 JSON으로 추출.
4. fixtures/에 직접 만든 가짜 HWPX 서식 3종.

수용 기준:
- 회사 데이터 입력/수정이 가능하다.
- 가짜 HWPX 3종에서 표 격자와 텍스트를 읽는다.
- 값은 만들지 않고 읽기만 한다.
```

---

## M9. HWPX 서식 채우기와 bid_context 재사용

```text
docs/PROJECT_SPEC.md의 8.9를 읽고 M9를 진행해줘. 계획 먼저.

목표: HWPX 입찰서식을 채우고, 채운 정보를 PPT 생성의 bid_context로 재사용한다.

할 일:
1. prompts/form_map.md: 격자 JSON + 회사 데이터 항목 목록 -> 셀별 대응. 값은 만들지 않는다.
2. core/hwpx/fill.py: 대응표대로 DB 값 채우기, 반복 행 복제, 원본 zip 순서와 압축 방식 유지.
3. /forms: 서식 업로드 -> 대응 확인 -> 채우기 -> 다운로드.
4. 채워진 데이터 구조를 bid_contexts.data로 저장.

수용 기준:
- 가짜 서식 3종이 채워진 HWPX로 나온다.
- AI 대응 결과에 값(이름, 숫자)이 들어 있으면 거부한다.
- 인력 3명이면 행이 3개로 늘어난다.
- 채운 정보가 PPT 생성 입력으로 보인다.
```

---

## M10. 템플릿 검색과 즐겨찾기

```text
docs/PROJECT_SPEC.md의 후순위 검색 범위를 읽고 M10을 진행해줘. 계획 먼저.

목표: 템플릿이 많아졌을 때 분야, 기관, 사용 이력, 별표로 찾을 수 있게 한다.

할 일:
1. template_stars, template_usage_stats.
2. 템플릿 목록 검색/필터/정렬.
3. 후순위 옵션으로 템플릿 원문 임베딩과 의미 검색.

수용 기준:
- 템플릿 200개 가짜 데이터에서 검색/필터가 1초 안에 응답한다.
- 별표 토글이 동작한다.
```

---

## M11. 구글 드라이브, 구글 로그인, 사무실 PC 배포

```text
docs/PROJECT_SPEC.md의 실행 환경과 비기능 요구사항을 읽고 M11을 진행해줘. 계획 먼저.

할 일:
1. SOURCE=gdrive: 서비스 계정 키(.env 경로)로 지정 폴더 재귀 조회.
2. 템플릿 PPTX와 공고/과업 문서 변경 감지.
3. 구글 로그인(회사 도메인만 허용). 관리자 이메일 목록은 .env.
4. 백업: 매일 pg_dump -> data/backups(7일 보관) -> 드라이브 업로드 옵션.
5. docs/DEPLOY.md 작성.

수용 기준:
- 드라이브 폴더에 새 템플릿을 넣으면 다음 주기에 템플릿 목록에 나타난다.
- 회사 도메인이 아닌 계정은 로그인할 수 없다.
- 백업 파일로 빈 DB에 복구하는 절차를 실제로 한 번 실행해 DEPLOY.md에 결과를 남긴다.
```

---

## M12. 나라장터 공고 탐색 데모

```text
docs/PROJECT_SPEC.md의 공고 탐색 후순위 범위를 읽고 M12를 진행해줘. 계획 먼저. 데모 수준이다.

할 일:
1. 공공데이터포털 조달청 나라장터 입찰공고정보서비스의 용역 공고 조회 API를 조사해 보고한다(구현 전).
2. core/notices/client.py: 기간·키워드로 공고 조회, notices 테이블 저장.
3. config/notice_rules.yaml 규칙 점수 계산.
4. 상위 N건 AI 3줄 요약.
5. /notices: 점수순 목록, 요약, "사업 카드 만들기".

수용 기준:
- 실제 인증키로 최근 7일 용역 공고를 가져와 점수순으로 보여준다.
- "사업 카드 만들기"로 만든 카드에서 공고/과업 입력 단계로 이어진다.
```

---

## 아래 내용은 v0.1 원문이며, v0.2 섹션과 충돌하면 v0.2를 우선한다.

Claude Code나 Codex에 그대로 붙여넣어 쓰는 마일스톤별 프롬프트다.

## 사용법

1. 빈 저장소를 만들고 루트에 `AGENTS.md`, `CLAUDE.md`, `docs/PROJECT_SPEC.md`, `docs/PROMPTS.md`를 넣어 첫 커밋을 한다.
2. 마일스톤은 순서대로 하나씩 진행한다. 아래 코드 블록 하나를 통째로 복사해 에이전트에 붙여넣는다.
3. 에이전트가 계획을 먼저 보여주면 읽고 승인한다. Claude Code는 계획 모드를 쓰면 편하다.
4. 끝나면 수용 기준을 사람이 직접 실행해서 확인하고, 맨 아래 "리뷰 프롬프트"를 다른 에이전트(예: 구현은 Claude Code, 리뷰는 Codex)에 돌린다.
5. 문제없으면 마일스톤 단위로 커밋하고 태그(`m0`, `m1` ...)를 단다.
6. 회사 실제 제안서는 저장소가 아니라 `data/import/`에 넣는다(gitignore 대상).

사람이 미리 준비할 것: Anthropic API 키(월 사용 한도 설정), 회사 폰트 파일(`./fonts`), 시험용 제안서 5~10건과 `projects.csv`.

---

## M0. 저장소 뼈대와 실행 환경

```text
AGENTS.md와 docs/PROJECT_SPEC.md의 5장(시스템 구성), 6장(데이터 모델)을 읽고 M0을 진행해줘.
먼저 만들 파일 목록과 순서를 계획으로 보여주고 승인받은 뒤 구현해.

목표: 아무 기능 없이도 전체 구성이 한 번에 뜨고, 이후 작업이 올라갈 뼈대를 만든다.

할 일:
1. AGENTS.md의 저장소 구조대로 폴더를 만든다. backend는 uv 프로젝트, web은 Next.js(App Router, TypeScript, Tailwind).
2. docker-compose.yml: db(pgvector 공식 이미지, PostgreSQL 16), redis, api, worker, web.
   - worker 이미지에 LibreOffice(headless), poppler-utils, fontconfig, 기본 한글 폰트(Noto Sans CJK 등)를 설치하고 ./fonts를 /usr/share/fonts/company에 읽기 전용 마운트.
   - ./data를 api와 worker에 마운트.
3. backend: FastAPI 앱, pydantic-settings 설정(.env), SQLAlchemy 2 + Alembic, Celery 앱, 공통 jobs 테이블.
   - 첫 마이그레이션: pgvector 확장 활성화, jobs 테이블.
   - GET /health: db, redis, worker(ping 작업) 상태를 반환.
   - GET /health/fonts: worker에서 fc-list 결과 중 company 폰트 목록 반환.
4. web: 첫 화면에서 /health 결과를 보여준다.
5. Makefile: up, down, migrate, test, lint, shell.
6. .env.example(키 이름만), .gitignore(data/, fonts/, .env 포함), config/ 아래 PROJECT_SPEC 7장의 설정 파일 초안(labels.yaml, palettes.yaml, pricing.yaml은 빈 값).
7. GitHub Actions: backend pytest, ruff, web 타입체크와 빌드.

수용 기준:
- make up 후 http://localhost:3000 에서 db, redis, worker가 모두 정상으로 보인다.
- make migrate가 빈 DB에서 성공한다.
- make test, make lint가 통과한다.
- ./fonts에 폰트 파일을 넣고 재시작하면 /health/fonts에 나온다.

하지 말 것: 기능 화면, 인증, AI 연동은 아직 만들지 않는다.
```

---

## M1. 가져오기, PPTX 분해, 렌더링

```text
docs/PROJECT_SPEC.md의 6.1, 6.2, 8.1, 8.2, 8.3을 읽고 M1을 진행해줘. 계획 먼저 보여줘.

목표: data/import 폴더의 사업 폴더들을 읽어 사업 카드, 문서, 슬라이드를 만들고 썸네일까지 생성한다.

할 일:
1. DB: projects, documents, slides 테이블과 마이그레이션(6장 필드 중 embedding 제외).
2. core/pptx/extract.py: PPTX 경로를 받아 슬라이드별 추출 결과(제목, 텍스트, 표 마크다운, 노트, 도형 목록, 통계, 색, 폰트)를 데이터 객체로 반환. DB에 의존하지 않는다.
   - 제목 휴리스틱, 도형 읽는 순서, 그룹 도형 재귀, 테마 색 해석과 lumMod/lumOff/tint/shade 반영은 8.2를 따른다.
3. core/pptx/render.py: 원본 복사본을 임시 폴더에서 PDF로 변환하고 슬라이드별 PNG(가로 480, 1600) 생성. 시간 제한과 실패 시 오류 메시지.
4. core/pptx/fonts.py: 사용 폰트 목록과 설치 여부 비교.
5. worker 작업: import_folder → (사업별) register_documents → (PPTX별) process_pptx(추출+렌더링+저장).
   - 원본은 data/originals/<sha256>.<ext>로 복사하고 읽기 전용 권한. 같은 해시는 건너뛴다.
   - 파일 종류는 파일명 규칙으로 추정(8.1).
   - projects.csv가 있으면 사업 정보를 채운다.
6. API: POST /imports(가져오기 시작), GET /jobs/{id}, GET /projects, GET /projects/{id}, GET /documents/{id}/slides.
7. 테스트: python-pptx로 가짜 덱을 만드는 헬퍼(tests/factories.py)를 만들고, 그룹 도형·표·테마 색·placeholder 제목이 들어간 덱으로 extract를 검증. render는 LibreOffice가 있는 환경에서만 도는 통합 테스트로.

수용 기준:
- data/import에 사업 폴더 3개(가짜 덱 가능)를 두고 POST /imports를 호출하면 jobs가 끝나고 slides 행과 썸네일 파일이 생긴다.
- 같은 가져오기를 다시 실행하면 새로 처리되는 문서가 0건이다.
- data/originals의 파일은 수정되지 않는다(해시 비교 테스트).
- 회사 폰트가 없는 덱은 documents.fonts_missing에 기록된다.
- 80장 덱 처리 시간이 로그에 남는다.

하지 말 것: 화면, AI, 구글 드라이브.
```

---

## M2. 사업 카드와 장표 라이브러리 화면

```text
docs/PROJECT_SPEC.md의 3장, 8.5(P1 부분), 9장을 읽고 M2를 진행해줘. 계획 먼저.

목표: 실무자가 사업 카드를 관리하고 장표를 썸네일로 찾아볼 수 있게 한다.

할 일:
1. API: 사업 카드 생성·수정(이름, 기관, 분야, 연도, 금액, 수주 여부, 점수, 메모), 문서 업로드(사업 카드에 파일 추가 → process 작업), 썸네일·미리보기 이미지 제공.
2. API: GET /slides 검색. 필터(분야, 연도 범위, 수주 여부, 기관, 장), 키워드(제목·텍스트·설명 부분 일치), 정렬(수주 우선 → 별표 → 최신), 페이지네이션.
3. web:
   - /projects 목록과 필터, 새 카드 만들기.
   - /projects/[id] 상세: 정보 편집, 문서 목록과 처리 상태, 파일 올리기.
   - /library: 왼쪽 필터, 위 검색창, 썸네일 그리드(무한 스크롤), 카드 아래 사업명·연도·수주 표시. 클릭하면 크게 보기, 원본 사업·파일·슬라이드 번호, 추출 텍스트.
   - / 대시보드: 진행 중 사업 카드와 최근 작업.
4. usage_events 테이블과 기록(search, view_slide).

수용 기준:
- 장표 2,000장 가짜 데이터에서 필터+키워드 검색이 1초 안에 응답한다(인덱스 확인).
- 사업 정보를 화면에서 수정하면 라이브러리 필터에 바로 반영된다.
- 처리 중인 문서는 진행 상태가 보이고, 실패하면 이유가 한 문장으로 보인다.

하지 말 것: 장 구분 AI, 바구니, 덱 만들기.
```

---

## M3. AI 장 구분, 슬라이드 설명, 확인 화면

```text
docs/PROJECT_SPEC.md의 4장, 7장(labels.yaml), 8.4, 10장을 읽고 M3을 진행해줘. 계획 먼저.

목표: AI가 슬라이드마다 장을 붙이고 한 줄 설명을 쓰며, 사람이 빠르게 확인·수정할 수 있게 한다.

할 일:
1. core/ai/client.py: anthropic SDK 래퍼.
   - 모델·최대 토큰은 설정에서, 프롬프트는 prompts/<name>.md를 읽어 변수 치환, 내용 해시 계산.
   - 응답을 Pydantic 모델로 검증, 형식 오류 시 최대 2회 재시도.
   - ai_calls 테이블에 모델, prompt_name, prompt_hash, 토큰, 비용(config/pricing.yaml), 대상, 지연, 상태 기록.
   - AI_ENABLED=false면 호출하지 않고 None 반환. 테스트용 mock 모드.
2. prompts/chapter_segment.md, prompts/slide_describe.md 작성.
   - 장 구분: 슬라이드 번호·제목 목록 + 목차로 보이는 슬라이드 이미지 → 각 슬라이드 chapter_key와 confidence. labels.yaml 목록 밖은 unknown. 장은 연속 구간.
   - 설명: 썸네일+텍스트 → 60자 이내, 기관명·지역명·수치 넣지 않기.
3. 후처리: 1~2장짜리로 끊긴 장 구간을 앞뒤 장에 맞춰 보정(확신도 낮을 때만).
4. worker 작업: label_document(장 구분 → 설명). process_pptx가 끝나면 자동으로 이어서 실행.
5. slide_label_events, 확인 상태 필드 마이그레이션.
6. web:
   - /review: 확신도 낮은 순 대기열. 썸네일 크게, 현재 장 표시, Enter=확인, 숫자키=장 선택, 덱 단위 "나머지 모두 확인".
   - /library 필터에 장 추가, 카드에 장 표시.
   - /settings: 장 목록·분야 보기(편집은 관리자만), AI 사용량·비용 월별 합계.
7. evals/chapter/: 사람 정답 CSV(document, slide_index, chapter_key) 형식과 정확도 계산 스크립트.

수용 기준:
- 가짜 덱 3개(mock 응답)로 전체 흐름이 돌고, 실제 키로는 live 테스트 1건이 돈다.
- 모든 AI 호출이 ai_calls에 비용과 함께 기록된다.
- 확인 화면에서 바꾼 장은 chapter_source=human, chapter_confirmed=true로 저장되고 이벤트가 남는다.
- labels.yaml에 없는 키는 저장되지 않는다(테스트).
- evals 스크립트가 정답 CSV와 비교해 정확도를 출력한다.

하지 말 것: 글 바꾸기, 임베딩.
```

---

## M4. 슬라이드 합치기 (스파이크 → 구현)

```text
docs/PROJECT_SPEC.md의 8.6을 읽고 M4를 진행해줘. 이 작업은 두 단계다.

1단계: 스파이크 (구현 전에 결과를 보고하고 멈출 것)
- tests/factories.py로 서로 다른 테마·마스터를 가진 가짜 덱 5종을 만든다: 그룹 도형, 표, 차트, 그림, placeholder 상속 제목, 테마 색(schemeClr) 사용 도형, 배경 그림 포함.
- core/pptx/merge.py에 SlideMerger 인터페이스(merge(items: list[(pptx_path, slide_index)], base_template: path|None) -> output_path)를 정의한다.
- python 백엔드를 시험 구현한다: 도형 트리·배경 복사, 그림/차트/미디어 파트 복사와 rId 재연결, placeholder 상속 위치·서식과 테마 색·폰트를 명시 값으로 굳히기.
- 평가: 각 결과 슬라이드를 렌더링해 원본과 SSIM 비교, LibreOffice로 열리는지, 파일 구조 검증(관계 누락 없음).
- Aspose.Slides 평가판과 파워포인트 자동화는 설치 없이 문서 조사만 해서 장단점을 정리한다.
- 결과 표(케이스별 SSIM, 실패 원인)와 추천안을 보고하고 멈춘다.

2단계: 승인된 방식으로 구현
- 선택한 백엔드를 완성하고 나머지는 인터페이스만 남긴다(설정으로 선택).
- 수용 기준: 5종 케이스 모두 SSIM 0.95 이상, 결과 파일이 LibreOffice에서 경고 없이 열림, 원본 파일 불변. 파워포인트 확인은 사람이 결과 파일로 한다(확인 대상 파일을 data/outputs/m4_check/에 남겨줘).

하지 말 것: 색 바꾸기, 글 바꾸기, 화면.
```

---

## M5. 덱 빌더 (새 사업 카드 → 장별 후보 → 바구니 → 만들기)

```text
docs/PROJECT_SPEC.md의 3장 시나리오, 6.3, 9장(/decks)을 읽고 M5를 진행해줘. 계획 먼저.

목표: 실무자가 새 사업 카드에서 장별로 장표를 골라 하나의 PPTX를 받는다.

할 일:
1. DB: decks, deck_items.
2. API: 덱 생성(사업 카드 기준), 장 순서 설정(labels.yaml 기본 순서에서 시작), 장별 후보 장표 조회(같은 장 + 같은 분야 우선, 수주 우선, 별표, 최신), 바구니 항목 추가·삭제·순서 변경, 만들기(작업), 다운로드.
3. worker 작업 build_deck: deck_items 순서대로 M4 merger로 합치기 → data/outputs/<deck_id>.pptx. 진행률 갱신.
4. web /decks/[id]:
   - 왼쪽: 장 목록(순서 드래그), 장마다 담긴 장표 수.
   - 가운데: 선택한 장의 후보 장표 썸네일 그리드(필터: 분야, 수주만, 기관). 클릭으로 담기.
   - 오른쪽: 바구니(순서 드래그, 빼기), 만들기 버튼, 진행 상태, 다운로드.
   - /projects/[id]에서 "새 제안서 만들기" 진입.
5. /library에서도 "바구니에 담기" 가능(진행 중인 덱 선택).
6. usage_events: add_to_cart, build_deck, download.

수용 기준:
- 사업 카드 생성 → 장 3개에서 장표 6장 담기 → 만들기 → 다운로드까지 화면에서 끝까지 된다.
- 결과 PPTX의 장표 순서가 바구니 순서와 같다.
- 30장 덱 만들기가 1분 안에 끝난다.

하지 말 것: 색 바꾸기(M6), 잔존 검사(M7), 글 바꾸기(M9).
```

---

## M6. 색 바꾸기

```text
docs/PROJECT_SPEC.md의 7장(palettes.yaml), 8.7을 읽고 M6을 진행해줘. 계획 먼저.

목표: 가져온 장표의 색을 이번 사업 카드의 팔레트로 바꾼다.

할 일:
1. core/pptx/recolor.py:
   - analyze(slide) → 색 묶음 목록(대표색, 면적 가중치, 역할 후보). 흰색 근처·검정 근처·저채도 회색 제외.
   - plan(analysis, palette) → 묶음별 대상 색(밝기 차이 유지 규칙 포함).
   - apply(slide, plan) → 도형 채우기·선·글자·표 셀 색 교체. 테마 색 참조는 해석 후 명시 색으로.
   - 그림 면적 비율이 높으면 경고.
2. build_deck에 색 바꾸기 단계 추가. deck에 palette_key, deck_items에 장표별 색 계획(사람이 수정한 값) 저장.
3. web: 덱 빌더에 팔레트 선택, 장표 미리보기(바뀐 색으로 렌더링한 썸네일), 묶음별 대상 색 수정.
4. 테스트: 단색·명도 변형·테마 색·표 셀 색이 섞인 가짜 장표로 교체 결과의 색 값 검증, 렌더링 비교로 회색·흰색이 바뀌지 않았는지 확인.

수용 기준:
- 주색이 파랑인 장표를 팔레트 primary=녹색으로 바꾸면 주색 묶음과 그 명도 변형이 모두 녹색 계열이 되고, 회색·흰색·검정은 그대로다.
- 그림 위주 장표는 리포트에 "색 변경 일부만 적용"으로 표시된다.
- 원본 파일 불변.

하지 말 것: 레이아웃 변경, 글 바꾸기.
```

---

## M7. 잔존 검사와 리포트 (P1 완료)

```text
docs/PROJECT_SPEC.md의 8.8을 읽고 M7을 진행해줘. 계획 먼저.

목표: 결과 덱에 이전 사업의 기관명·지역명·사업명 등이 남아 있으면 찾아서 알려준다.

할 일:
1. core/entities/residual.py:
   - build_terms(source_project, target_project) → 검사할 용어 목록(기관, 상위 기관, 사업명, 지명 추출, 연도 표기). 대상 사업에도 있는 값은 제외.
   - scan(pptx_path, terms) → [{slide_no, shape_id, term, context}].
   - 지명 추출 규칙(OO시/군/구/도, 특별시·광역시 등)과 띄어쓰기 변형 처리.
2. build_deck 마지막 단계에 잔존 검사를 추가하고 decks.report에 저장. 각 장표의 원본 사업 기준으로 검사.
3. web: 덱 빌더에서 장표별 경고 배지, 리포트 패널(장표, 도형, 발견 용어, 앞뒤 문맥), 다운로드 시 리포트 텍스트 파일 함께 제공.
4. 테스트: 표 안, 그룹 도형 안, 띄어쓰기 변형("OO 시")이 있는 경우 모두 찾는지.

수용 기준:
- 원본 기관명이 표 셀과 그룹 도형 안에 남은 가짜 덱에서 모두 찾는다.
- 새 사업과 같은 기관은 경고하지 않는다.
- P1 전체 흐름(가져오기 → 확인 → 덱 만들기 → 색 → 잔존 검사 → 다운로드)이 AI_ENABLED=false에서도 장 구분 없이 동작한다(장 필터만 비활성).

하지 말 것: AI 고유명사 추출(M9에서).
```

---

## M8. 의미 검색과 유사 과업 추천, 별표

```text
docs/PROJECT_SPEC.md의 8.5(P2), 8.9를 읽고 M8을 진행해줘. 계획 먼저.

할 일:
1. worker에 sentence-transformers + BAAI/bge-m3 로드(모델 캐시는 볼륨). slides.embedding(vector 1024)과 인덱스 마이그레이션.
2. embed_slides 작업: 제목+설명+텍스트 임베딩. 새 슬라이드 처리 후 자동 실행, 전체 재계산 명령 제공.
3. 검색: 키워드 결과와 의미 검색 결과를 RRF로 합치는 옵션(기본 켬).
4. 과업 요약: 사업 카드에 과업지시서(HWPX 또는 PDF)가 있으면 prompts/task_summary.md로 요약(주요 과업, 지역, 분야) → projects에 task_summary, task_embedding 저장. 과업지시서가 없는 과거 사업은 understanding 장 텍스트로 대신.
   - HWPX 텍스트 추출은 core/hwpx/read.py(문단과 표 텍스트)로 구현.
5. 덱 빌더 후보 정렬: 유사도 + 수주 가산 + 별표 가산 + 최신 가산(가중치는 config). 후보 카드에 "유사 사업: OO" 표시.
6. 별표: slide_stars, star_count, 라이브러리와 덱 빌더에서 별표 토글.

수용 기준:
- "체류형 관광"으로 검색하면 해당 단어가 없어도 의미가 비슷한 장표가 상위에 나온다(가짜 데이터로 테스트 케이스 작성).
- 과업지시서를 올린 새 사업 카드에서 장을 고르면 유사 사업의 장표가 위에 온다.
- 임베딩 처리 실패가 다른 처리를 막지 않는다.
```

---

## M9. AI 글 바꾸기

```text
docs/PROJECT_SPEC.md의 4장, 8.10, 10장을 읽고 M9를 진행해줘. 계획 먼저.

목표: 장표별로 "글 바꿔서 가져오기"를 고르면 AI가 도형별 글을 이번 과업에 맞게 바꾸고, 사람이 확인한 뒤 덱에 반영한다.

할 일:
1. prompts/rewrite_slide.md: 입력(도형별 원문·글자 수, 새 사업 카드, 과업 요약, 금지 표현) → 출력 {shape_id: new_text}.
   - 글자 수 85~115%, 근거 없는 수치·날짜·금액은 [확인 필요], 기관명·지역명은 새 사업 값만.
2. core/pptx/rewrite.py: 검증(글자 수, 금지 표현, 잔존 용어, 새로 생긴 숫자 탐지)과 적용(문단 첫 run 서식 유지, 문단 수 변화 처리).
3. prompts/extract_entities.md: 원본 문서 고유명사 추출 → 잔존 검사 용어에 추가.
4. 덱 빌더: 장표별 모드 토글(그대로/글 바꾸기), 글 바꾸기 결과를 도형별 원문·새 글 나란히 보여주고 수정 가능, 검증 경고 표시, 확정한 것만 build_deck에 반영.
5. evals/rewrite/: 글자 수 준수율, 잔존 0건 비율, 금지 표현 0건 비율, [확인 필요] 개수 계산 스크립트.
6. usage_events: choose_mode, edit_rewrite(수정한 글자 수).

수용 기준:
- 글 바꾸기 결과에 원본 기관명이 남으면 경고가 뜨고 확정 전에 보인다.
- 원본에 없던 숫자가 생기면 경고한다.
- 적용 후 렌더링해서 글이 칸을 넘치는 장표를 표시한다(텍스트 박스 경계 기준 간이 검사).
- 모드를 "그대로"로 둔 장표는 글이 하나도 바뀌지 않는다.
```

---

## M10. 구글 드라이브, 구글 로그인, 사무실 PC 배포

```text
docs/PROJECT_SPEC.md의 8.1(gdrive), 11장을 읽고 M10을 진행해줘. 계획 먼저.

할 일:
1. SOURCE=gdrive: 서비스 계정 키(.env 경로)로 지정 폴더 재귀 조회, 파일 ID·수정 시각으로 변경 감지, 사업 정보는 지정한 구글 시트에서 읽기. 주기 실행(기본 30분)과 수동 실행.
2. 결과 덱을 구글 드라이브 지정 폴더에도 저장하는 옵션.
3. 구글 로그인(회사 도메인만 허용). 관리자 이메일 목록은 .env. usage_events와 라벨 이벤트에 사용자 이메일 기록.
4. 백업: 매일 pg_dump → data/backups(7일 보관) → 드라이브 업로드 옵션.
5. 배포 문서 docs/DEPLOY.md: 사무실 PC 준비(OS, Docker 설치, 폰트, .env), 업데이트 방법, 백업 복구 방법, 장애 시 확인 순서.

수용 기준:
- 드라이브 폴더에 새 제안서를 넣으면 다음 주기에 라이브러리에 나타난다.
- 회사 도메인이 아닌 계정은 로그인할 수 없다.
- 백업 파일로 빈 DB에 복구하는 절차를 실제로 한 번 실행해 DEPLOY.md에 결과를 남긴다.
```

---

## M11. 입찰 서식(HWPX) 채우기 데모

```text
docs/PROJECT_SPEC.md의 6.5, 8.11을 읽고 M11을 진행해줘. 계획 먼저. 데모 수준이다.

할 일:
1. 회사 데이터 테이블(company_profile, personnel, personnel_careers, track_records)과 /company 입력 화면(엑셀 붙여넣기 지원이면 좋음).
2. core/hwpx/read.py 확장: 표를 셀 좌표 격자 JSON으로(병합 셀 정보 포함).
3. prompts/form_map.md: 격자 JSON + 회사 데이터 항목 목록 → 셀별 대응({cell: field_key} 와 반복 행 지정). 값은 만들지 않는다.
4. core/hwpx/fill.py: 대응표대로 DB 값 채우기, 반복 행 복제, zip 재압축 시 원본 파일 순서와 압축 방식 유지.
5. /forms: 서식 HWPX 올리기 → AI 대응 결과를 표 미리보기 위에 표시 → 사람이 수정·확정 → 채우기 → 다운로드.
6. fixtures/에 직접 만든 가짜 서식 3종(일반 현황, 참여 인력, 수행 실적)을 두고 테스트.

수용 기준:
- 가짜 서식 3종이 채워진 HWPX로 나오고, 사람이 한글에서 열어 확인할 파일을 data/outputs/m11_check/에 남긴다.
- AI 대응 결과에 값(이름, 숫자)이 들어 있으면 거부한다.
- 인력 3명이면 행이 3개로 늘어난다.

하지 말 것: HWP(구형) 처리, 자동 제출.
```

---

## M12. 나라장터 공고 탐색 데모

```text
docs/PROJECT_SPEC.md의 6.6, 8.12를 읽고 M12를 진행해줘. 계획 먼저. 데모 수준이다.

할 일:
1. 공공데이터포털 조달청 나라장터 입찰공고정보서비스의 용역 공고 조회 API를 조사해 엔드포인트, 필수 파라미터, 응답 필드, 첨부 문서 제공 여부를 정리해 보고한다(구현 전).
2. core/notices/client.py: 기간·키워드로 공고 조회, notices 테이블 저장(공고번호 기준 중복 제거).
3. config/notice_rules.yaml 규칙 점수 계산(포함·제외 키워드, 업종, 금액 범위, 지역, 남은 일수, 가중치).
4. 상위 N건 AI 3줄 요약(prompts/notice_summary.md, 공고명·기관·금액·첨부 텍스트가 있으면 포함).
5. /notices: 점수순 목록, 요약, "제외", "사업 카드 만들기"(projects.stage=exploring, 공고 정보 복사, 첨부 문서가 있으면 가져오기).
6. 매일 아침 1회 자동 조회 옵션.

수용 기준:
- 실제 인증키로 최근 7일 용역 공고를 가져와 점수순으로 보여준다.
- "사업 카드 만들기"로 만든 카드에서 바로 덱 빌더로 이어진다.
```

---

## 리뷰 프롬프트 (다른 에이전트에 돌릴 것)

```text
이 저장소의 AGENTS.md와 docs/PROJECT_SPEC.md를 읽고, 방금 끝난 마일스톤 <M번호>의 변경 사항(git diff <이전 태그>..HEAD)을 리뷰해줘.

확인할 것:
1. AGENTS.md 절대 원칙 위반: 원본 파일 수정 가능성, AI가 디자인·사실 정보를 생성하는 경로, client.py를 거치지 않는 AI 호출, 비밀값 노출.
2. docs/PROMPTS.md의 해당 마일스톤 수용 기준 중 테스트나 코드로 확인되지 않는 항목.
3. 경계 조건: 빈 파일, 손상된 PPTX, 매우 큰 파일, 한글 파일명, 동시에 두 작업이 같은 문서를 처리하는 경우.
4. 테스트가 실제로 검증하는지(항상 통과하는 테스트, 지나치게 느슨한 기준).
5. 범위 밖으로 미리 만든 기능.

결과는 심각도(반드시 수정 / 수정 권장 / 참고)로 나눠 파일과 줄 번호와 함께 알려줘. 직접 고치지는 말고 목록만.
```

## 막혔을 때 쓰는 프롬프트

```text
<문제 상황>을 해결하려다 막혔어. 바로 고치지 말고 먼저:
1. 지금까지 확인된 사실과 추측을 나눠서 정리하고,
2. 원인 후보를 가능성 높은 순서로 3개 이내로 들고,
3. 각 후보를 확인할 가장 작은 실험을 제안해줘.
AGENTS.md의 원칙을 바꿔야 해결되는 문제라면 그 점을 명시하고 내 판단을 기다려.
```
