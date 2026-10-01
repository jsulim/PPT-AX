# AGENTS.md — 인트윈 제안 자동화 플랫폼

이 파일은 코딩 에이전트(Codex, Claude Code 등)가 이 저장소에서 작업할 때 항상 따르는 규칙이다.
기능과 범위의 기준은 `docs/PROJECT_SPEC.md`, 작업 단위 지시는 `docs/PROMPTS.md`에 있다.
작업을 시작하기 전에 두 문서에서 이번 작업과 관련된 부분을 반드시 읽는다.

## 프로젝트 한 줄 요약

공고문·과업지시서와 입찰서식/사업 카드의 확정 정보를 바탕으로, 사람이 고른 기존 제안서 PPTX를
장표 유형 모음으로 쓰고 텍스트만 바꿔 새 제안서 초안을 만드는 사내 웹 도구. 사실 값은 코드가
그대로 채우고, AI는 서술 슬롯의 문장 교체와 슬롯·요구사항 연결만 돕는다.

## 절대 원칙 (어기면 안 됨)

1. **디자인은 원본 템플릿을 쓴다.** AI가 슬라이드 디자인(도형 배치, 박스, 아이콘, 색 조합)을 새로 생성하는 코드를 만들지 않는다. AI는 서술 슬롯의 글만 바꾼다.
2. **원본 파일은 읽기 전용이다.** `data/originals/` 아래 파일을 수정·덮어쓰기·삭제하지 않는다. 모든 결과물은 새 파일로 `data/outputs/`에 만든다.
3. **사실 정보는 AI가 만들지 않는다.** 금액, 점수, 수주 여부, 날짜, 사업명, 기관명, 참여 인력, 인력 경력, 수행 실적은 `bid_context`·`project_card`·DB·사람 입력에서만 온다. 사실 슬롯은 AI가 문장을 쓰지 않고 필드 연결만 제안하며, 실제 값은 코드가 JSON에서 그대로 치환한다.
4. **AI는 텍스트 슬롯만 다룬다.** PPTX 안의 텍스트 박스·표 셀·노트처럼 명시적으로 추출된 텍스트 자리만 교체 대상이다. 슬롯은 `fact`와 `narrative`로 나누고, AI 문장 생성은 `narrative` 슬롯에만 허용한다.
5. **AI 출력은 스키마로 검증한다.** 모든 AI 응답은 Pydantic 모델로 파싱·검증하고, 실패하면 정해진 횟수만 재시도한 뒤 사람 확인 대기 상태로 넘긴다.
6. **모든 AI 호출은 `core/ai/client.py`를 거친다.** 직접 SDK를 호출하지 않는다. 이 모듈이 모델, 프롬프트 버전(해시), 토큰, 비용, 대상 객체를 `ai_calls` 테이블에 기록한다.
7. **AI와 구글 연동 없이도 핵심 기능이 돌아가야 한다.** `AI_ENABLED=false`, `SOURCE=local`일 때 템플릿 가져오기, 사람이 지정한 슬롯·개요, 사실 슬롯 치환, 복사본 생성, 잔존 검사가 동작해야 한다.
8. **요구사항은 출처 있는 목록으로 관리한다.** 공고문·과업지시서·배점표는 자유 요약보다 요구사항 번호, 출처 쪽수, 배점 항목 목록을 우선 저장하고, 각 장표가 어떤 요구사항을 다루는지 연결한다.
9. **템플릿은 한 벌이 아니라 장표 유형 모음이다.** 초기에는 템플릿 PPT 하나를 사람이 고르더라도 데이터 모델에는 배점표 항목 → 장표 유형 → 장 수를 나타내는 `outline`을 둔다.
10. **비밀값은 코드와 저장소에 넣지 않는다.** API 키, 서비스 계정 키는 `.env`로만 받는다. `.env.example`에는 키 이름만 둔다.
11. **회사 실제 문서를 저장소에 커밋하지 않는다.** 테스트용 PPTX/HWPX는 테스트 코드가 직접 생성하거나 `fixtures/`에 직접 만든 가짜 문서만 둔다. `data/`는 gitignore.

## 저장소 구조

```
backend/            Python 프로젝트 (uv로 관리)
  app/              FastAPI (routers/, schemas/, services/, deps.py, main.py)
  worker/           Celery 작업 (ingest, render, label, embed, build_deck ...)
  core/             공용 로직 (UI·DB와 독립적으로 테스트 가능해야 함)
    pptx/           템플릿 텍스트 추출, 슬롯 매핑, 사실값 치환, 서술 글 교체, 복사본 저장, 잔존 검사 보조
    hwpx/           HWPX 읽기·채우기, 입찰정보 추출/정규화
    ai/             client.py, prompts 로더, 스키마
    entities/       잔존 검사(기관명·지역명 등)
    search/         후순위: 템플릿/과거 자료 검색
  db/               SQLAlchemy 모델, Alembic 마이그레이션
  tests/
web/                Next.js (App Router, TypeScript, Tailwind)
prompts/            AI 프롬프트 템플릿 (*.md). 버전은 git, 실행 시 내용 해시를 기록
config/             labels.yaml, palettes.yaml, banned_phrases.yaml, notice_rules.yaml, pricing.yaml
fixtures/           테스트용 가짜 문서
evals/              AI 품질 평가용 사람 정답 데이터와 스크립트
docs/               기획서와 작업 지시
data/               로컬 데이터 (gitignore): import/, originals/, thumbs/, outputs/, backups/
```

## 기술 스택 (임의로 바꾸지 않는다)

- Python 3.12, uv, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, Celery + Redis
- PostgreSQL 16 + pgvector
- python-pptx + lxml (PPTX), lxml + zipfile (HWPX)
- LibreOffice headless + poppler-utils(pdftoppm) (렌더링)
- anthropic Python SDK (Claude API), sentence-transformers + BAAI/bge-m3 (임베딩, P2부터)
- Next.js + TypeScript + Tailwind, 데이터 패칭은 TanStack Query
- Docker Compose로 로컬과 사무실 PC 모두 같은 방식으로 실행

새 라이브러리를 추가해야 하면 이유를 PR 설명이나 작업 보고에 한 줄로 남긴다.

## 자주 쓰는 명령

```
make up        # docker compose up -d --build
make down
make migrate   # alembic upgrade head
make test      # backend pytest + web 타입체크
make lint      # ruff, mypy(core/), eslint
make shell     # backend 컨테이너 셸
```

M0 작업에서 이 명령들을 실제로 만든다. 이후 작업은 이 명령으로 검증한다.

## 코드 규칙

- `core/`는 FastAPI, Celery, DB에 의존하지 않는 순수 함수·클래스로 만든다. 입력과 출력이 파일 경로나 데이터 객체여야 테스트가 쉽다.
- 함수와 변수 이름은 영어, 주석과 사용자에게 보이는 문구는 한국어.
- 사용자 화면 문구는 존댓말 평서문으로 짧게.
- 긴 작업(렌더링, AI 호출, 합치기)은 API에서 직접 하지 말고 Celery 작업으로 넘기고, `jobs` 테이블로 상태를 노출한다.
- 파일 경로는 `pathlib.Path`, 설정은 `pydantic-settings`.
- 예외를 삼키지 않는다. 사용자에게는 무엇이 실패했고 무엇을 하면 되는지 한 문장으로 보여준다.

## 테스트 규칙

- `core/`의 모든 공개 함수는 단위 테스트가 있어야 한다.
- PPTX 관련 테스트는 python-pptx로 가짜 덱을 생성해서 쓴다. 결과는 다시 열어서 구조(도형 수, 텍스트, 색 값)를 검사한다.
- 시각적 결과가 중요한 기능(합치기, 색 바꾸기)은 렌더링 이미지 비교(SSIM) 테스트를 둔다. 기준값은 테스트 코드에 명시한다.
- AI 호출은 테스트에서 mock 응답을 쓴다. 실제 API를 부르는 테스트는 `@pytest.mark.live`로 분리하고 기본 실행에서 제외한다.

## 작업 완료의 정의

1. 해당 작업의 수용 기준(`docs/PROMPTS.md`)을 모두 직접 실행해서 확인했다.
2. `make test`와 `make lint`가 통과한다.
3. DB 변경이 있으면 Alembic 마이그레이션이 있고, 빈 DB에서 `make migrate`가 성공한다.
4. 바뀐 점, 확인 방법, 남은 문제를 짧게 보고한다. 확인하지 못한 것은 확인했다고 쓰지 않는다.

## 하지 말 것

- 기획서 범위 밖 기능을 미리 만들지 않는다. 필요해 보이면 제안만 한다.
- 원본 파일 수정, 운영 데이터 삭제, `git push --force`, DB drop 같은 되돌릴 수 없는 작업을 하지 않는다.
- 테스트를 통과시키려고 테스트를 약하게 고치지 않는다.
- AI 프롬프트를 코드 문자열에 박지 않는다. `prompts/`에 둔다.
