# D3D Audit Report - audit_report_82.md

## 0. 감사 요약

- 감사 기준: `AI_AUDIT_DOC_STANDARD.md`
- 감사 방식: 재감사, 구현 중심 3-Pass 감사
- 감사 대상 경로: `/mnt/Projects_SSD/python/JissouParkEmpire`
- 직전 감사 문서: `audit_report_81.md`
- 새 보고서 번호: `audit_report_82.md`
- 감사일: 2026-06-02
- 수정 여부: 소스 코드 및 기존 문서 수정 없음. 본 감사 보고서만 신규 생성.
- 최종 판정: **HOLD**

81번 감사 이후 기준으로 현재 작업트리를 재검증했다. 결론은 81번과 동일하게 **실행 게이트는 통과하지만 PASS는 불가**다.

긍정적으로 확인된 사항은 다음과 같다.

- `pytest`, `pytest -W error`, `py_compile`, `git diff --check`, `git diff --cached --check`가 통과했다.
- `DATABASE_URL` 및 `SQLALCHEMY_DATABASE_URI` 우선순위 smoke가 통과했다.
- SQLite 연결 시 `journal_mode=wal`, `busy_timeout=5000`이 실제 적용된다.
- `FLASK_ENV=production DEBUG=true`에서도 `Config.DEBUG`가 `False`로 강제된다.
- `run.py` 기본 실행은 루프백 `127.0.0.1`로만 열린다.
- `FLASK_RUN_HOST=0.0.0.0`은 `ALLOW_UNSAFE_DEV_SERVER=1` 없이는 fail-closed 된다.
- XSS 정적/결합 회귀 테스트는 현재 코드에서 통과하며, 주요 `escapeHtml()` 제거 변형 4건을 모두 실패로 탐지했다.
- `BUILD_GUIDE.md`, `README.md`, `run.py`의 quickstart는 현재 Linux 호스트에 맞게 `python3` 또는 `venv/bin/python` 기준으로 정리되어 있다.

그러나 PASS 차단 사유가 남아 있다.

- 감사 산출물과 작업트리 변경분이 여전히 추적 가능한 상태로 정리되지 않았다.
- `README.md`의 주요 동시성 과보증은 상당히 완화됐지만, 번체/간체 섹션에 일부 잔여 표현이 있다.
- `README.md` 밖의 현재 하위 문서(`implementation_summary.md`, `DESIGN_DECISIONS.md`, `audit_roadmap.md`)에는 아직 실제 검증 강도보다 센 동시성/락 보증 표현이 남아 있다.
- `IMPLEMENTATION_SUMMARY.md`/`implementation_summary.md`, `LESSONS_LEARNED.md`/`lessons_learned.md` 파일명 authority가 불명확하다.
- 실제 PostgreSQL/MySQL row-lock/deadlock E2E와 실제 브라우저/jsdom DOM XSS E2E는 수행되지 않았다.
- CI/workflow 파일이 없어 품질 게이트가 로컬 수동 실행에 의존한다.

## 1. Audit Scope

### 1.1 포함 범위

- 감사 표준:
  - `AI_AUDIT_DOC_STANDARD.md`
- 직전 감사:
  - `audit_report_81.md`
- 주요 프로젝트 문서:
  - `spec.md`
  - `README.md`
  - `CHANGELOG.md`
  - `BUILD_GUIDE.md`
  - `DESIGN_DECISIONS.md`
  - `audit_roadmap.md`
  - `designs.md`
  - `implementation_summary.md`
  - `lessons_learned.md`
- 구현 파일:
  - `run.py`
  - `app/config.py`
  - `app/models.py`
  - `app/game_engine.py`
  - `app/npc_engine.py`
  - `app/routes/game_routes.py`
  - `app/static/js/game.js`
- 테스트 파일:
  - `tests/conftest.py`
  - `tests/test_regression.py`
- 로컬 상태:
  - `git status --short`
  - `git diff --stat`
  - `git diff --check`
  - `git diff --cached --check`
- 실행 게이트:
  - pytest 기본
  - pytest warning-as-error
  - Python syntax compile
  - DB config smoke
  - SQLite pragma smoke
  - 서버 바인딩 smoke
  - XSS mutation smoke
  - CI/workflow 파일 검색

### 1.2 감사 모델

`AI_AUDIT_DOC_STANDARD.md`의 3-Pass 모델을 적용했다.

- Pass 1: Implementation Compliance Audit
- Pass 2: Debug / Engineering Quality Audit
- Pass 3: Security Audit

## 2. Excluded Scope

- 소스 코드 수정: 사용자 지시에 따라 수행하지 않음
- 기존 문서 수정: 사용자 지시에 따라 수행하지 않음
- 실제 PostgreSQL/MySQL 서버 연결 및 row-lock/deadlock 부하 E2E: 로컬 인프라 미제공으로 제외
- 실제 브라우저 또는 jsdom 기반 DOM XSS E2E: 현재 테스트 스위트 밖으로 제외
- Gunicorn 실제 다중 worker 기동 및 부하 테스트: 문서/설정 smoke와 `run.py` 개발 서버 smoke로 대체
- `.antigravitycli/`: 현재 감사 대상 구현 변경 범위 밖
- `stitch_shitsiseki_empire_ui_refactor/`: 별도 참조/작업 디렉터리로 간주하고 본 감사 범위에서 제외

## 3. 직전 감사 요청사항 재확인

81번 보고서의 PASS 전 요구사항은 다음이었다.

| 81번 요구사항 | 82번 재감사 상태 | 판정 |
| --- | --- | --- |
| 감사 보고서와 modified 파일 추적성 정리 | `audit_report_73.md`-`audit_report_81.md`가 untracked이고 15개 tracked 파일이 modified 상태 | **Needs Fix / HOLD** |
| README 번체/간체 잔여 품질 문제 정리 | 일부 완화됐지만 간체 `强力结合`, `保证`, 번체 accepted-risk 문맥의 `確保` 잔여 | **Needs Fix / Minor** |
| required docs 파일명 authority 결정 | 대문자 required 파일은 없고 소문자 파일만 존재 | **Needs Spec Clarification** |
| 실제 RDBMS E2E와 브라우저/jsdom DOM XSS E2E 수행 또는 residual risk 유지 | 수행되지 않음. residual risk 유지 | **Accepted Risk / Residual Risk** |
| CI/workflow 부재 보완 | workflow 파일 없음 | **Known Operational Risk** |

추가로 82번 재감사에서는 `README.md` 외의 현재 하위 문서에도 과보증 표현이 남아 있음을 별도 finding으로 승격했다. 81번은 README 중심으로 판정했으나, `AI_AUDIT_DOC_STANDARD.md`의 문서-구현 양방향 정합성 기준상 `implementation_summary.md`, `DESIGN_DECISIONS.md`, `audit_roadmap.md`도 현재 운영 판단에 영향을 주는 authority 문서다.

## 4. Pass 1: Implementation Compliance Findings

## [IMP-F001] 감사 산출물과 작업트리 추적성이 여전히 PASS 기준에 미달한다

- Pass: Implementation Compliance
- Pattern: Audit Traceability / Source Control Hygiene
- Area: Git status, audit reports
- Severity: Major
- Status: Needs Fix / Hold
- Summary: 구현 게이트는 통과하지만 현재 변경 세트와 감사 산출물이 아직 추적 가능한 상태로 정리되지 않았다.
- Evidence:
  - `git status --short` 감사 시점 출력:
    - `M BUILD_GUIDE.md`
    - `M CHANGELOG.md`
    - `M DESIGN_DECISIONS.md`
    - `M README.md`
    - `M app/config.py`
    - `M app/game_engine.py`
    - `M app/npc_engine.py`
    - `M app/routes/game_routes.py`
    - `M app/static/js/game.js`
    - `M audit_roadmap.md`
    - `M designs.md`
    - `M lessons_learned.md`
    - `M run.py`
    - `M tests/conftest.py`
    - `M tests/test_regression.py`
    - `?? audit_report_73.md`
    - `?? audit_report_74.md`
    - `?? audit_report_75.md`
    - `?? audit_report_76.md`
    - `?? audit_report_77.md`
    - `?? audit_report_78.md`
    - `?? audit_report_79.md`
    - `?? audit_report_80.md`
    - `?? audit_report_81.md`
  - `git diff --stat`: 15 files changed, 218 insertions, 222 deletions
  - 본 보고서 작성 후 `audit_report_82.md` 역시 신규 감사 산출물로 추적 대상에 추가된다.
- Expected: PASS 전에는 감사 대상 변경과 감사 보고서의 보존/추적 정책이 명확해야 한다.
- Actual: 변경 파일과 감사 보고서가 여전히 untracked/modified 상태다.
- Impact: 이후 재감사에서 어떤 변경이 실제 구현 수정이고 어떤 변경이 감사 대응인지 구분하기 어렵다. 감사 증거의 immutable chain이 약하다.
- Suggested Fix: 감사 보고서 73-82 및 현재 변경 파일을 커밋, 별도 브랜치, 또는 명시적 immutable archive 정책으로 정리한다.
- Re-audit Method:
  - `git status --short`
  - `git diff --stat`
  - 최신 `audit_report_*.md` 연속성 확인
- Owner: Human / Maintainer
- Notes: 사용자 지시에 따라 이번 감사에서는 정리 작업을 수행하지 않았다.

## [IMP-F002] required documentation 파일명 authority가 여전히 불명확하다

- Pass: Implementation Compliance
- Pattern: Required Inputs / Documentation Authority
- Area: Required docs inventory
- Severity: Minor
- Status: Needs Spec Clarification
- Summary: 표준 문서와 AGENTS 규칙에서 요구하는 대문자 파일명이 실제 저장소의 소문자 파일명과 불일치한다.
- Evidence:
  - `IMPLEMENTATION_SUMMARY.md`: 없음
  - `LESSONS_LEARNED.md`: 없음
  - `implementation_summary.md`: 존재
  - `lessons_learned.md`: 존재
  - `ls -1 spec.md README.md CHANGELOG.md BUILD_GUIDE.md IMPLEMENTATION_SUMMARY.md implementation_summary.md LESSONS_LEARNED.md lessons_learned.md DESIGN_DECISIONS.md audit_roadmap.md designs.md AI_AUDIT_DOC_STANDARD.md`: 대문자 2개 파일 없음으로 exit code `2`
- Expected: required documentation set은 대소문자까지 포함해 하나의 authority를 가져야 한다.
- Actual: Linux 기준으로 대문자 required file은 누락 상태이고 소문자 파일만 존재한다.
- Impact: 자동 감사, cross-platform 작업, 외부 에이전트 실행 시 필수 문서 누락으로 판정될 수 있다.
- Suggested Fix: 대문자 파일명을 표준으로 만들지, 소문자 파일명을 표준으로 문서화할지 결정한다.
- Re-audit Method: required docs inventory 재실행.
- Owner: Architect / Human
- Notes: 이는 코드 결함은 아니지만 D3D required inputs 기준의 authority 문제다.

## [IMP-F003] README 다국어 과보증은 상당히 완화됐지만 일부 잔여 표현이 남아 있다

- Pass: Implementation Compliance
- Pattern: User-Facing Documentation / i18n Claim Strength
- Area: `README.md`
- Severity: Minor
- Status: Needs Fix
- Summary: 80번-81번의 Major 과보증은 대부분 해소됐지만, README 다국어 섹션에는 아직 검증 강도보다 센 표현 또는 번역 품질 잔여가 일부 남아 있다.
- Evidence:
  - `README.md:163`: 번체 accepted-risk 문맥에서 `ID Canonical Ordering 設計安全性`을 `確保`한다고 표현한다. 실제 RDBMS E2E가 없으므로 "설계상 위험을 낮춘다" 수준이 더 정확하다.
  - `README.md:193`: 간체 SQLite single worker 설명에 `保证开发和小规模托管的一致性`가 남아 있다.
  - `README.md:195`: 간체 PostgreSQL/MySQL 설명에 `强力结合`이 남아 있다.
  - `README.md:339`, `README.md:367`: `隔離交易` 번역은 문맥상 transaction을 뜻하지만 사용자-facing 문서에서는 의미 혼동 가능성이 있다.
  - `rg -n "工作工作|多工作工作"` 결과는 현재 출력 없음. 81번에서 언급된 간체 중복 오타는 현재 재현되지 않는다.
- Expected: README 다국어 섹션은 같은 의미와 같은 보증 강도를 유지해야 하며, 실제 검증이 없는 항목은 `위험 감소`, `설계상 완화`, `Accepted Risk` 수준으로 정렬해야 한다.
- Actual: 핵심 과보증은 낮아졌으나 일부 표현 강도와 번역 품질 잔여가 남아 있다.
- Impact: 사용자-facing 문서 신뢰도가 완전히 회복되지는 않았다.
- Suggested Fix: 번체/간체 매트릭스와 FAQ를 문장 단위로 다시 정렬한다.
- Re-audit Method:
  - `rg -n "strongly|highly|高度|強力|强力|保证|保證|確保|보장|確実|완전|완치|원천|철저히|강력히|강하게" README.md`
  - README 5개 언어 동시성 매트릭스 수동 대조
- Owner: Coder / Docs
- Notes: PASS 단독 차단급은 아니지만, 다른 문서 authority 문제와 결합되면 문서-구현 정합성 리스크를 키운다.

## [IMP-F004] README 밖의 현재 하위 문서에 검증 강도보다 센 동시성/락 보증 표현이 남아 있다

- Pass: Implementation Compliance
- Pattern: Source-Doc Bidirectional Consistency / Claim Strength Alignment
- Area: `implementation_summary.md`, `DESIGN_DECISIONS.md`, `audit_roadmap.md`
- Severity: Major
- Status: Needs Documentation Recovery / Hold
- Summary: README는 상당 부분 완화됐지만, 현재 구현 summary와 설계 결정 문서에는 실제 검증 범위를 넘어서는 "원천 소멸", "강력 예방", "고도 예방", "검증 완료" 계열 표현이 남아 있다. 이는 `Accepted Risk`와 충돌한다.
- Evidence:
  - `implementation_summary.md:340`: 선점 락을 `원천 소멸`한다고 표현.
  - `implementation_summary.md:342`: 최상단 비관적 락을 `영구히 제거`, 선점 락 현상을 `원천 소멸`했다고 표현.
  - `implementation_summary.md:343`-`345`: `영구 교착 상태 강력 예방`, DB 커넥션 풀 고갈 결함 발생 위험을 `강력히 예방`했다고 표현.
  - `implementation_summary.md:350`: 실제 RDBMS E2E 미검증을 괄호로 인정하지만, 앞 문장에서는 "높은 수준의 동시성 격리 무결성"을 확보할 수 있도록 구성됐다고 표현.
  - `implementation_summary.md:481`: SQLite single worker에서 일관성이 `보장됩니다`, `온전히 유지됩니다`라고 표현.
  - `implementation_summary.md:483`: PostgreSQL/MySQL 이주 시 deadlock 발생 위험을 `고도로 예방`한다고 표현.
  - `DESIGN_DECISIONS.md:656`: 선점 락을 `고도로 해제(소멸)`했다고 표현.
  - `DESIGN_DECISIONS.md:665`: DB 커넥션 고갈 위협을 `고도로 소멸`했다고 표현.
  - `audit_roadmap.md:110`-`129`: 여러 항목을 `✅` 및 `검증 완료`로 표시하지만, 실제 이번 감사에서 확인한 테스트는 7개 pytest 및 smoke 중심이며 실제 RDBMS/브라우저 E2E는 제외 범위다.
- Expected: 현재 authority 문서는 실제 검증 수준과 동일한 강도로 표현해야 한다. 미검증 항목은 `Accepted Risk`, `Residual Risk`, `설계상 완화`, `로컬 테스트 범위 내 검증`으로 제한해야 한다.
- Actual: 일부 현재 문서가 검증 범위보다 강한 완료/보증 언어를 유지한다.
- Impact: 감사자가 README만 보면 위험이 관리된 것으로 보이지만, 하위 authority 문서를 보면 더 강한 보증을 주장한다. 이는 문서 간 authority 충돌이며, 실제 RDBMS/브라우저 E2E 없는 상태에서 PASS 판정 근거를 흐린다.
- Suggested Fix:
  - `implementation_summary.md`와 `DESIGN_DECISIONS.md`의 강한 표현을 `위험 완화`, `설계상 저감`, `로컬 회귀 테스트 범위 내 검증`으로 낮춘다.
  - `audit_roadmap.md`의 `✅ 검증 완료` 항목 중 실제 E2E 미수행 항목은 `Accepted Risk` 또는 `Manual Smoke Verified`로 분리한다.
  - historical changelog를 보존할지 현재 기준으로 정정할지 별도 authority 정책을 둔다.
- Re-audit Method:
  - `rg -n "완벽|원천|완전|철저|극대|고도|보장|근본|영구|무결|완치|완전히|전수" CHANGELOG.md DESIGN_DECISIONS.md designs.md implementation_summary.md lessons_learned.md app tests`
  - `audit_roadmap.md`의 각 `✅` 항목과 실제 테스트/스모크 증거 매핑
- Owner: Architect / Docs
- Notes: 이 finding은 82번에서 새로 명시적으로 승격했다. 81번의 README 중심 finding만으로는 현재 문서 authority 충돌을 충분히 덮지 못한다.

## [IMP-F005] `BUILD_GUIDE.md` quickstart의 `python` 명령 의존은 해소됐다

- Pass: Implementation Compliance
- Pattern: Build Guide / Runtime Reproducibility
- Area: `BUILD_GUIDE.md`, `README.md`, `run.py`
- Severity: Info
- Status: Verified
- Summary: 현재 Linux 호스트에서 `python` 명령은 없지만, quickstart는 `python3` 또는 `venv/bin/python` 기준으로 정리되어 있다.
- Evidence:
  - `command -v python`: exit code `1`
  - `command -v python3`: `/usr/bin/python3`
  - `BUILD_GUIDE.md:17`: `python3 -m venv venv`
  - `BUILD_GUIDE.md:27`: `python3 run.py`
  - `BUILD_GUIDE.md:30`: `venv/bin/python run.py`
  - `README.md:40`: `python3 -m venv venv`
  - `README.md:45`: `python3 run.py`
  - `README.md:47`: `venv/bin/python run.py`
  - `run.py:7`: `venv/bin/python run.py` 및 `python3 run.py` 안내
- Expected: 현재 Linux 환경에서 바로 재현 가능한 명령을 우선 제시해야 한다.
- Actual: `python3` 우선으로 정리됐다.
- Impact: 신규 운영자의 quickstart 실패 가능성이 낮아졌다.
- Suggested Fix: 없음.
- Re-audit Method: `command -v python`, `command -v python3`, BUILD_GUIDE/README 명령 재확인.
- Owner: Coder

## [IMP-F006] 주요 구현 경로는 현재 문서의 완화된 방향과 대체로 일치한다

- Pass: Implementation Compliance
- Pattern: Code-Doc Alignment / Runtime Defaults
- Area: `run.py`, `app/config.py`, `app/models.py`, `app/game_engine.py`, `app/static/js/game.js`
- Severity: Info
- Status: Verified
- Summary: 실제 구현은 "위험 제거"가 아니라 "fail-closed, 위험 완화, accepted risk" 모델에 가깝고, 이 방향 자체는 코드에서 확인된다.
- Evidence:
  - `run.py:22`-`27`: 루프백이면 개발 편의를 위해 `DEBUG=true`, 개발용 `SECRET_KEY`를 setdefault로 주입.
  - `run.py:31`-`37`: 외부 바인딩은 `ALLOW_UNSAFE_DEV_SERVER` 없으면 `ValueError`.
  - `run.py:39`-`44`: 외부 바인딩에서 기본 개발용 secret 사용 금지.
  - `app/config.py:41`-`44`: explicit production이면 `DEBUG=False` 강제.
  - `app/config.py:49`-`55`: production 또는 non-debug에서 secret 누락 시 fail-closed.
  - `app/config.py:60`: `SQLALCHEMY_DATABASE_URI`가 `DATABASE_URL`보다 우선한다.
  - `app/models.py:533`-`546`: SQLite 연결 시 WAL과 busy_timeout PRAGMA 적용.
  - `app/game_engine.py:195`-`204`: NPC 기본 턴 처리 후 commit으로 선점 락을 해제하고 별도 단계에서 `process_npc_turn()` 실행.
  - `app/static/js/game.js:105`, `133`, `136`, `153`: 사용자/서버 동적 문자열이 `escapeHtml()`로 감싸져 있다.
- Expected: 코드가 문서의 안전 경계와 같은 방향이어야 한다.
- Actual: 구현 자체는 완화/방어 모델로 정렬되어 있다.
- Impact: PASS 차단 사유는 주로 추적성, 문서 authority, 미수행 E2E, CI 부재다. 현재 검토 범위에서 신규 Critical 구현 결함은 발견하지 못했다.
- Suggested Fix: 문서 강도를 코드 검증 강도에 맞춰 낮춘다.
- Re-audit Method: 위 라인 재확인 및 smoke 재실행.
- Owner: Auditor

## 5. Pass 2: Debug / Engineering Quality Findings

## [DBG-F001] Python 회귀 테스트와 warning-as-error 게이트는 통과한다

- Pass: Debug / Engineering Quality
- Pattern: Deterministic Test Gate
- Area: pytest
- Severity: Info
- Status: Verified
- Summary: 현재 로컬 pytest 7개는 모두 통과한다.
- Evidence:
  - `env PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -q -p no:cacheprovider`
  - 결과: `7 passed in 0.29s`
  - `env PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -q -W error -p no:cacheprovider`
  - 결과: `7 passed in 0.33s`
  - `rg -n "^def test_" tests`:
    - `test_audit_report_57_savepoint_flush`
    - `test_audit_report_59_spy_overcrowding_lock`
    - `test_audit_report_61_npc_attack_lock_order`
    - `test_xss_escape_html`
    - `test_sqlite_lost_update_race_condition`
    - `test_database_url_env_fallback`
    - `test_static_js_inner_html_xss_protection`
- Expected: 모든 회귀 테스트가 통과해야 한다.
- Actual: 통과.
- Impact: 현재 로컬 단위/결합 테스트 범위에서는 기능 실패가 없다.
- Suggested Fix: 없음.
- Re-audit Method: 동일 명령 재실행.
- Owner: Coder

## [DBG-F002] 테스트 범위는 `audit_roadmap.md`의 완료 표현보다 좁다

- Pass: Debug / Engineering Quality
- Pattern: Test Coverage / Roadmap Evidence Mismatch
- Area: `tests/test_regression.py`, `audit_roadmap.md`
- Severity: Major
- Status: Needs Documentation Recovery / Accepted Risk
- Summary: 실제 테스트 스위트는 7개 회귀 테스트와 smoke 중심이다. 반면 `audit_roadmap.md`는 T1-T26 및 Phase 8 항목 다수를 `✅`, `검증 완료`로 표시한다.
- Evidence:
  - 실제 pytest 함수 수: 7개
  - `audit_roadmap.md:110`-`129`: Phase 8의 주요 동시성/보안 항목이 `✅`로 표시됨.
  - `audit_roadmap.md:113`: 전투 피해 평균 시나리오.
  - `audit_roadmap.md:116`: Gunicorn 프로세스 락 확보.
  - `audit_roadmap.md:128`: 밀사 overcrowding Lost Update 방지 검증 완료.
  - `audit_roadmap.md:129`: NPC 공격 락 순서 역전 데드락 완화.
  - 이번 감사에서 실제 Gunicorn 다중 worker 부하, 실제 PostgreSQL/MySQL, 브라우저 DOM E2E는 제외 범위다.
- Expected: roadmap의 `검증 완료`는 현재 실행 가능한 테스트나 보존된 수동 evidence와 직접 연결되어야 한다.
- Actual: 일부 항목은 현재 로컬 pytest/smoke 증거보다 넓게 완료 표시되어 있다.
- Impact: 다음 감사자가 roadmap만 보고 실제 검증 범위를 과대평가할 수 있다.
- Suggested Fix: roadmap 항목을 `Automated Verified`, `Manual Smoke Verified`, `Accepted Risk`, `Not Yet E2E Verified`로 분리한다.
- Re-audit Method:
  - `rg -n "^def test_" tests`
  - `audit_roadmap.md` T1-T26 항목별 자동/수동 증거 매핑
- Owner: Architect / QA
- Notes: 이 finding은 소스 코드 실패가 아니라 품질 게이트 evidence mapping 문제다.

## [DBG-F003] 문법/공백 품질 게이트는 통과한다

- Pass: Debug / Engineering Quality
- Pattern: Static Quality Gate
- Area: Python syntax, whitespace
- Severity: Info
- Status: Verified
- Evidence:
  - `env PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m py_compile app/__init__.py app/battle_engine.py app/config.py app/game_engine.py app/models.py app/npc_engine.py app/routes/auth_routes.py app/routes/game_routes.py run.py tests/conftest.py tests/test_regression.py`: exit code `0`
  - `git diff --check`: exit code `0`
  - `git diff --cached --check`: exit code `0`
- Expected: syntax error와 whitespace error가 없어야 한다.
- Actual: 통과.
- Impact: 정적 품질 게이트에서는 차단 이슈가 없다.
- Suggested Fix: 없음.
- Re-audit Method: 동일 명령 재실행.
- Owner: Coder

## [DBG-F004] DB 설정과 SQLite PRAGMA smoke는 통과한다

- Pass: Debug / Engineering Quality
- Pattern: Runtime Config / DB Portability
- Area: `app/config.py`, `app/models.py`, SQLAlchemy setup
- Severity: Info
- Status: Verified
- Evidence:
  - `SECRET_KEY=smoke-secret DATABASE_URL=postgresql://u:p@localhost:5432/jissou_audit ...`: `postgresql://u:p@localhost:5432/jissou_audit`
  - `SECRET_KEY=smoke-secret SQLALCHEMY_DATABASE_URI=postgresql://u:p@localhost:5432/jissou_uri ...`: `postgresql://u:p@localhost:5432/jissou_uri`
  - `import psycopg2`: `2.9.12 (dt dec pq3 ext lo64)`
  - SQLite `journal_mode`: `wal`
  - SQLite `busy_timeout`: `5000`
- Expected: 환경변수 우선순위와 SQLite 완화 설정이 실제 런타임에서 확인되어야 한다.
- Actual: smoke 범위에서 확인됐다.
- Impact: 설정 wiring은 정상이다.
- Suggested Fix: 실제 RDBMS E2E는 별도 Accepted Risk로 유지한다.
- Re-audit Method: 동일 smoke 및 실제 DB E2E.
- Owner: Coder

## [DBG-F005] CI/workflow 파일은 여전히 없다

- Pass: Debug / Engineering Quality
- Pattern: CI / Reproducibility
- Area: CI/CD
- Severity: Minor
- Status: Accepted Risk / Known Operational Risk
- Evidence:
  - `rg --files -g .github/** -g *workflow* -g *ci*`: exit code `1`, 출력 없음
- Expected: 최소한 pytest, warning-as-error, diff check, compile gate가 CI 또는 명시적 수동 evidence 정책에 연결되어야 한다.
- Actual: CI 파일이 없다.
- Impact: 현재 품질 보증은 감사자가 로컬에서 수동 실행한 결과에 의존한다.
- Suggested Fix: 최소 GitHub Actions 또는 로컬 수동 gate evidence archive 정책을 도입한다.
- Re-audit Method: `.github/workflows` 또는 대체 수동 evidence 문서 확인.
- Owner: Maintainer

## 6. Pass 3: Security Findings

## [SEC-F001] 개발 서버 네트워크 노출 fail-closed는 구현 및 smoke로 확인됐다

- Pass: Security
- Pattern: Network Bind / Debug Console Boundary
- Area: `run.py`
- Severity: Info
- Status: Verified
- Summary: 기본 기동은 루프백으로 제한되고, 외부 바인딩은 명시 opt-in 없이는 실패한다.
- Evidence:
  - 기본 기동 명령:
    - `timeout 3 env SECRET_KEY=smoke-secret DATABASE_URL=sqlite:////tmp/jissou-run-82-default.db PYTHONDONTWRITEBYTECODE=1 venv/bin/python run.py`
  - 출력:
    - `Jissou Park Empire v1.8.9`
    - `Running on http://127.0.0.1:5000`
    - timeout exit code `124`는 서버가 정상 기동 중이어서 시간 제한으로 종료된 기대 결과다.
  - 외부 바인딩 차단 명령:
    - `timeout 3 env FLASK_RUN_HOST=0.0.0.0 SECRET_KEY=smoke-secret DATABASE_URL=sqlite:////tmp/jissou-run-82-blocked.db PYTHONDONTWRITEBYTECODE=1 venv/bin/python run.py`
  - 결과:
    - exit code `1`
    - `ValueError: CRITICAL SECURITY ERROR: 외부 바인딩... ALLOW_UNSAFE_DEV_SERVER=1 ...`
  - 외부 바인딩 opt-in 명령:
    - `timeout 3 env FLASK_RUN_HOST=0.0.0.0 ALLOW_UNSAFE_DEV_SERVER=1 SECRET_KEY=custom-key DATABASE_URL=sqlite:////tmp/jissou-run-82-unsafe.db PYTHONDONTWRITEBYTECODE=1 venv/bin/python run.py`
  - 출력:
    - `Debug mode: off`
    - `Running on all addresses (0.0.0.0)`
- Expected: 개발 서버가 기본값으로 LAN에 열리면 안 된다.
- Actual: 기본은 loopback, 외부 바인딩은 opt-in 필요.
- Impact: debug console LAN 노출 위험이 기본값에서 차단된다.
- Suggested Fix: 없음.
- Re-audit Method: 위 3개 smoke 재실행.
- Owner: Coder

## [SEC-F002] production debug 및 secret fail-closed 경계는 smoke로 확인됐다

- Pass: Security
- Pattern: Secret / Production Debug Boundary
- Area: `app/config.py`
- Severity: Info
- Status: Verified
- Evidence:
  - `env FLASK_ENV=production DEBUG=true SECRET_KEY=prod-secret PYTHONDONTWRITEBYTECODE=1 venv/bin/python -c "from app.config import Config; print(Config.DEBUG); print(len(Config.SECRET_KEY))"`
  - 출력:
    - `False`
    - `11`
  - `app/config.py:41`-`44`: explicit production이면 `DEBUG = False`
  - `app/config.py:49`-`55`: production 또는 non-debug에서 secret 누락 시 `ValueError`
- Expected: production에서 `DEBUG=true` 오설정이 그대로 적용되면 안 되며, secret 누락 fallback이 허용되면 안 된다.
- Actual: production debug는 강제 off 된다.
- Impact: 개발용 debug backend 및 임시 secret 노출 가능성이 낮아진다.
- Suggested Fix: secret 누락 실패 경로도 별도 smoke로 추가하면 더 좋다.
- Re-audit Method: production debug/secret smoke 재실행.
- Owner: Coder

## [SEC-F003] XSS 정적/결합 회귀 테스트는 mutation smoke까지 통과하지만 DOM E2E는 남은 리스크다

- Pass: Security
- Pattern: XSS / Static and Mutation Guard
- Area: `app/static/js/game.js`, `tests/test_regression.py`
- Severity: Minor
- Status: Verified with Residual Risk
- Summary: 현재 정적/결합 테스트는 `escapeHtml()` 누락 변형을 잡는다. 다만 실제 브라우저 DOM 삽입 경로 E2E는 수행되지 않았다.
- Evidence:
  - `app/static/js/game.js:105`: `${escapeHtml(parkName)}`
  - `app/static/js/game.js:133`: `${escapeHtml(data.error || I18N.scoutFail)}`
  - `app/static/js/game.js:136`: `${escapeHtml(err.message)}`
  - `app/static/js/game.js:153`: `${escapeHtml(targetName)}`
  - `tests/test_regression.py:376`-`395`: `innerHTML` 대입문 정적 스캔.
  - `tests/test_regression.py:397`-`433`: HTML builder template literal 전수 스캔.
  - mutation smoke 결과:
    - `current PASS`
    - `parkName FAILS_AS_EXPECTED`
    - `targetName FAILS_AS_EXPECTED`
    - `data.error FAILS_AS_EXPECTED`
    - `err.message FAILS_AS_EXPECTED`
- Expected: 정찰/공격 모달의 사용자 또는 서버 유래 문자열은 escape되어야 한다.
- Actual: 현재 코드와 mutation smoke는 통과한다.
- Impact: 정적 누락 회귀는 강하게 잡히지만, 브라우저 DOM 파서/런타임 특이점까지 검증하지는 않는다.
- Suggested Fix: jsdom 또는 실제 브라우저 기반 DOM E2E를 추가한다.
- Re-audit Method: 기존 pytest, mutation smoke, 브라우저/jsdom E2E 재실행.
- Owner: Coder / QA

## [SEC-F004] 실제 PostgreSQL/MySQL row-lock/deadlock E2E는 아직 미수행이다

- Pass: Security
- Pattern: Concurrency Boundary / External DB Validation
- Area: PostgreSQL/MySQL production target
- Severity: Major
- Status: Accepted Risk
- Summary: 코드와 문서는 PostgreSQL/MySQL로 이주할 때 row-lock 기반 정합성이 좋아질 것을 전제로 하지만, 실제 DB 인스턴스에서 row-lock/deadlock 부하 검증은 수행되지 않았다.
- Evidence:
  - PostgreSQL URI smoke와 `psycopg2` import는 통과했다.
  - 실제 PostgreSQL/MySQL 서버 접속, schema migration, Gunicorn multi-worker 부하, deadlock/lock timeout 로그 검증은 수행하지 않았다.
  - `README.md`, `implementation_summary.md` 일부는 accepted risk를 명시한다.
- Expected: `Target Production`을 최종 PASS로 올리려면 실제 대상 DB에서 동시성 E2E가 필요하다.
- Actual: Accepted Risk로 유지된다.
- Impact: 운영 DB에서 lock timeout/deadlock 가능성을 배제할 수 없다.
- Suggested Fix: PostgreSQL/MySQL 테스트 인스턴스와 Gunicorn 다중 worker 부하 테스트를 추가한다.
- Re-audit Method:
  - 실제 DB에 schema 생성
  - Gunicorn multi-worker 실행
  - T13/T19/T25/T26 계열 동시성 부하 스크립트 수행
  - deadlock/lock timeout 로그 확인
- Owner: Architect / QA

## [SEC-F005] SQLite multi-worker 경합은 WAL/busy_timeout으로 완화됐지만 hard guarantee가 아니다

- Pass: Security
- Pattern: DB Locking / Accepted Risk
- Area: SQLite default DB
- Severity: Major
- Status: Accepted Risk
- Summary: SQLite 연결 PRAGMA는 실제 적용되지만, SQLite의 단일 writer 모델과 `with_for_update()` no-op 제약은 남아 있다.
- Evidence:
  - `app/models.py:533`-`546`: SQLite connect event에서 WAL과 busy_timeout 적용.
  - SQLite smoke:
    - `journal_mode`: `wal`
    - `busy_timeout`: `5000`
  - `tests/test_regression.py:268`: SQLite lost update race condition 테스트는 존재하지만 실제 multi-process Gunicorn SQLite 부하 테스트는 아니다.
- Expected: SQLite multi-worker는 제한 지원/accepted risk로만 표기되어야 한다.
- Actual: 코드 완화는 있으나 hard guarantee는 아니다.
- Impact: 고부하 다중 쓰기 상황에서 `Database Locked` 또는 timeout 가능성이 남는다.
- Suggested Fix: SQLite 운영 한계를 문서 전체에서 일관되게 유지하고, 운영 한계 초과 시 PostgreSQL 전환 조건을 명확히 한다.
- Re-audit Method: SQLite multi-process write contention smoke 또는 PostgreSQL 전환 테스트.
- Owner: Architect / Maintainer

## 7. Cross-Pass Conflicts

## [XPF-F001] 실행 게이트는 통과하지만 추적성 미정리로 PASS 근거가 약하다

- Pass: Cross-Pass
- Severity: Major
- Status: Hold
- Summary: 테스트, 설정 smoke, 보안 smoke는 통과하지만 변경 파일과 감사 보고서가 여전히 untracked/modified 상태다.
- Evidence:
  - `pytest`: pass
  - `pytest -W error`: pass
  - config/server/XSS smoke: pass
  - `git status --short`: 15개 tracked 파일 modified, `audit_report_73.md`-`audit_report_81.md` untracked
- Impact: PASS 판정 시점의 immutable evidence가 부족하다.
- Suggested Fix: 감사 산출물과 변경분 추적 정책 정리.

## [XPF-F002] README의 claim은 개선됐지만 하위 authority 문서는 아직 강한 표현을 유지한다

- Pass: Cross-Pass
- Severity: Major
- Status: Hold
- Summary: README의 주요 과보증은 상당히 낮아졌지만 `implementation_summary.md`, `DESIGN_DECISIONS.md`, `audit_roadmap.md`는 아직 실제 E2E 미수행 상태보다 강한 완료/보증 표현을 포함한다.
- Evidence:
  - `README.md`: 주요 PostgreSQL/MySQL 문맥은 accepted risk와 위험 감소 중심으로 개선.
  - `implementation_summary.md:340`-`345`, `483`: 강한 예방/보증 표현 잔존.
  - `DESIGN_DECISIONS.md:665`: `고도로 소멸`.
  - `audit_roadmap.md:110`-`129`: `✅`, `검증 완료`.
- Impact: 문서 간 authority 충돌로 인해 운영자가 실제 검증 범위를 오해할 수 있다.
- Suggested Fix: 모든 현재 문서를 같은 claim-strength 정책으로 정렬.

## [XPF-F003] Accepted Risk와 Phase 완료 표기가 같은 항목에 공존한다

- Pass: Cross-Pass
- Severity: Major
- Status: Needs Documentation Recovery
- Summary: 실제 PostgreSQL/MySQL row-lock/deadlock E2E와 브라우저 DOM E2E는 accepted/residual risk인데, roadmap 일부는 관련 동시성/보안 항목을 완료로 표시한다.
- Evidence:
  - Excluded Scope: 실제 RDBMS E2E, 브라우저 DOM E2E 제외.
  - `audit_roadmap.md:116`, `128`, `129`: 동시성 항목 `✅`.
  - `README.md`, `implementation_summary.md`: 일부 accepted risk 명시.
- Impact: Phase gate 기준이 "코드가 존재한다"인지 "실환경 검증까지 완료"인지 불명확하다.
- Suggested Fix: Phase gate 용어를 `Implemented`, `Local Regression Verified`, `Production E2E Verified`, `Accepted Risk`로 분리.

## 8. Required Fixes Before PASS

1. `audit_report_73.md`-`audit_report_82.md` 및 현재 modified 파일들의 추적성 정책을 정리한다.
2. `implementation_summary.md`, `DESIGN_DECISIONS.md`, `audit_roadmap.md`의 강한 동시성/락 보증 표현을 실제 검증 수준에 맞춘다.
3. README 번체/간체 섹션의 잔여 표현 강도와 번역 품질 문제를 정리한다.
4. `IMPLEMENTATION_SUMMARY.md`/`implementation_summary.md`, `LESSONS_LEARNED.md`/`lessons_learned.md` 파일명 authority를 결정한다.
5. 실제 PostgreSQL/MySQL E2E와 브라우저/jsdom DOM XSS E2E는 수행하거나, 현재처럼 residual risk로 남긴다는 gate 기준을 명확히 한다.
6. CI/workflow 부재를 수동 gate evidence archive 정책 또는 최소 CI로 보완한다.

## 9. Accepted Risks

| Risk | Status | Owner | Revisit Trigger |
| --- | --- | --- | --- |
| SQLite multi-worker `Database Locked` 가능성 | Accepted Risk | Project Lead Architect / Eunho Lim | DAU 100명 초과, 초당 DB 쓰기 10회 초과, locked error 주 3회 이상 |
| 실제 PostgreSQL/MySQL row-lock/deadlock E2E 미수행 | Accepted Risk | Project Lead Architect / Eunho Lim | 실제 RDBMS 이주, lock timeout/deadlock 주 1회 이상 |
| 실제 브라우저/jsdom DOM XSS E2E 미수행 | Known Residual Risk | Coder / QA | 브라우저/jsdom 테스트 추가 전까지 |
| CI/workflow 부재 | Known Operational Risk | Maintainer | CI 도입 또는 수동 gate evidence 아카이브 |
| historical 문서의 과거 강한 표현 보존 여부 | Needs Spec Clarification | Architect / Human | 현재 문서 authority 정책 결정 전까지 |

## 10. Needs Spec Clarification

1. 감사 보고서가 untracked 상태로 누적될 때 PASS 전 필수 커밋이 필요한지, 별도 archive 보존으로 충분한지 기준이 필요하다.
2. historical changelog와 lessons 문서의 강한 표현을 현재 감사 기준으로 모두 낮출지, 당시 릴리스 기록으로 보존할지 기준이 필요하다.
3. required documentation 파일명의 대소문자 표준을 결정해야 한다.
4. Node.js 정적/결합 XSS 검증을 충분한 gate로 볼지, 브라우저/jsdom DOM E2E를 필수로 볼지 결정해야 한다.
5. 실제 PostgreSQL/MySQL E2E 전에도 다국어 README와 implementation summary에서 `Target Production` 표현을 유지할 수 있는지, `Target Production Design / Accepted Risk`로 제한할지 결정해야 한다.
6. `audit_roadmap.md`의 `✅`가 "구현 존재", "로컬 테스트 통과", "실환경 E2E 통과" 중 무엇을 의미하는지 명확히 해야 한다.

## 11. 검사한 케이스

- `AI_AUDIT_DOC_STANDARD.md` 확인.
- 최신 감사 보고서 번호 확인: `audit_report_81.md` 이후 `audit_report_82.md`.
- `test -f audit_report_82.md`: 기존 파일 없음 확인.
- 직전 감사 `audit_report_81.md` HOLD 사유 확인.
- `git status --short`.
- `git diff --stat`.
- `git diff --check`.
- `git diff --cached --check`.
- `env PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -q -p no:cacheprovider`: `7 passed in 0.29s`.
- `env PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -q -W error -p no:cacheprovider`: `7 passed in 0.33s`.
- `env PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m py_compile ...`: pass.
- PostgreSQL URI smoke via `DATABASE_URL`: pass.
- PostgreSQL URI smoke via `SQLALCHEMY_DATABASE_URI`: pass.
- `psycopg2` import smoke: `2.9.12`.
- SQLite `journal_mode`: `wal`.
- SQLite `busy_timeout`: `5000`.
- production `DEBUG=true` 강제 off smoke: `False`.
- loopback 개발 서버 smoke: `127.0.0.1`, `v1.8.9`.
- 외부 바인딩 fail-closed smoke: `ValueError`.
- 외부 바인딩 opt-in debug off smoke: `0.0.0.0`, `Debug mode: off`.
- XSS mutation smoke: 주요 guard 제거 4건 모두 `FAILS_AS_EXPECTED`.
- README 다국어 hard-boundary 표현 재검색.
- implementation/design/roadmap 강한 claim 표현 검색.
- Gunicorn bind 문서 검색.
- CI/workflow 파일 검색: 없음.
- required docs 파일명 inventory 확인.

## 12. 제외한 케이스

- 실제 PostgreSQL/MySQL 서버 기반 row-lock/deadlock E2E.
- 실제 Gunicorn multi-worker 부하 테스트.
- 실제 브라우저/jsdom DOM XSS E2E.
- 장시간 soak test.
- 운영 로그 기반 lock timeout/deadlock 검증.
- 외부 네트워크 의존성 업데이트 및 패키지 업그레이드.

## 13. Re-audit Checklist

- [x] `AI_AUDIT_DOC_STANDARD.md` 확인
- [x] `audit_report_81.md` 확인
- [x] `audit_report_82.md` 기존 파일 없음 확인
- [x] 현재 작업트리 상태 확인
- [x] pytest 기본 게이트 통과 확인
- [x] pytest warning-as-error 게이트 통과 확인
- [x] py_compile 통과 확인
- [x] diff whitespace gate 통과 확인
- [x] DB config smoke 통과 확인
- [x] SQLite PRAGMA smoke 통과 확인
- [x] production DEBUG smoke 통과 확인
- [x] 서버 바인딩 smoke 통과 확인
- [x] XSS mutation smoke 통과 확인
- [x] README 다국어 잔여 표현 확인
- [x] 하위 문서 claim strength 확인
- [x] required docs 파일명 authority 확인
- [x] CI/workflow 부재 확인
- [ ] 감사 산출물 및 변경 파일 추적성 정리
- [ ] 실제 PostgreSQL/MySQL row-lock/deadlock E2E
- [ ] 실제 브라우저/jsdom DOM XSS E2E
- [ ] CI 또는 수동 gate evidence archive 정책 수립

## 14. Final Decision

**HOLD**

현재 구현과 실행 게이트만 보면 신규 Critical 구현 결함은 발견하지 못했다.

- `pytest`: 7 passed
- `pytest -W error`: 7 passed
- `py_compile`: pass
- `git diff --check`: pass
- DB config smoke: pass
- SQLite WAL/busy_timeout smoke: pass
- 개발 서버 loopback/fail-closed smoke: pass
- XSS mutation smoke: pass

하지만 D3D 감사 기준의 PASS는 "코드가 로컬 테스트를 통과했다"만으로는 부족하다. 현재 PASS를 막는 이유는 다음과 같다.

1. 감사 보고서와 modified 파일 추적성이 아직 정리되지 않았다.
2. README 밖의 현재 authority 문서에도 실제 검증 강도보다 센 동시성/락 보증 표현이 남아 있다.
3. README 번체/간체 섹션에 일부 표현 강도 및 번역 품질 잔여가 있다.
4. required documentation 파일명의 대소문자 authority가 불명확하다.
5. 실제 RDBMS row-lock/deadlock E2E와 브라우저 DOM XSS E2E는 여전히 residual risk다.
6. CI/workflow 부재는 수동 gate 의존 상태로 남아 있다.

따라서 82번 재감사의 최종 판정은 **HOLD**다. 소스 코드와 기존 문서는 수정하지 않았고, 감사 결과 문서 `audit_report_82.md`만 생성했다.
