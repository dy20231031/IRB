# IRB 제출 준비 도우미

연구자의 답변을 바탕으로 기관별 제출 항목과 근거를 정리하는 질문형 AI Agent MVP입니다. **가톨릭대학교 성심교정과 서울교육대학교**의 공개 자료를 초기 데이터로 사용합니다.

**현재 범위:** 성인이 스스로 동의할 수 있는 설문 또는 인터뷰 연구의 신규심의 준비, 일반 동의 절차. 실제 접수 자격, 승인 여부, 심의면제 가능성은 결정하지 않습니다. 기관 담당자 검수 전인 개발용 버전입니다.

## 구현된 기능

- 기관과 연구 조건 입력, AI가 추출한 사실의 사용자 확인
- 미확인 사실에 따라 추가 질문 선택: 최대 2회, 회당 질문 묶음 3개
- 준비 필요 / 현재 조건에서 비해당 / 확인 필요의 3단계 판단
- 판단 근거, 사용한 답변, 규칙 버전, 공식 출처와 확인일 표시
- 파일 준비와 eIRB 입력 과제 구분
- 필요 여부와 사용자가 표시하는 준비 상태 구분
- 결과를 Markdown과 JSON으로 내려받기, 답변 수정 후 재판단
- API 키 없이 객관식 실행. 설정하면 OpenAI Responses API로 주관식 사실 추출
- 29개 초기 규칙, 22개 사실 항목, 6개 추가 질문 묶음

예를 들어 **“전화번호는 받지 않지만 이름은 받는다”**는 답변이면 참가자 개인정보 동의서를 준비 대상으로 표시합니다. 전화번호를 받지 않는다는 답 하나로 서류를 제외하지 않습니다. 연구자 본인의 개인정보 동의서는 별도 항목입니다.

## 실행하기

Python **3.12**와 Git을 사용합니다. 다운로드 ZIP으로 받은 경우 압축을 푼 폴더에서 가상환경 생성 단계부터 실행하세요.

### Windows PowerShell

```powershell
git clone https://github.com/dy20231031/IRB.git
cd IRB
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

### macOS / Linux

```bash
git clone https://github.com/dy20231031/IRB.git
cd IRB
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

브라우저에서 `http://localhost:8501`을 엽니다. 기본값은 로컬 실행입니다. **“예시로 흐름 확인하기”**에서 가상 사례를 선택하면 빠르게 볼 수 있습니다. 종료는 터미널에서 `Ctrl+C`입니다.

가상환경 활성화 명령을 사용하지 않아 PowerShell 실행 정책을 바꾸지 않아도 됩니다. 위 Python 실행 파일 경로가 없으면 현재 폴더가 `IRB`인지 확인하세요.

## AI 사실 추출 켜기 (선택)

1. `.env.example`을 복사하여 `.env` 파일을 만듭니다.
2. `OPENAI_API_KEY`에 본인의 API 키를, `OPENAI_MODEL`에 사용 가능한 모델 ID를 입력합니다.
3. 앱을 다시 실행하고 **연구 설명을 OpenAI API로 보내 사실 추출 제안 받기**를 선택합니다.

모델은 Responses API의 Structured Outputs를 지원해야 합니다. [공식 모델 목록](https://developers.openai.com/api/docs/models)과 [Structured Outputs 사용법](https://developers.openai.com/api/docs/guides/structured-outputs)을 확인하세요. 모델은 코드에서 고정하지 않습니다.

API 키와 모델이 설정되지 않으면 객관식으로 동작합니다. API 요청 실패, 구조화 응답 오류, 원문 근거 불일치 시에도 객관식으로 계속할 수 있습니다. 설정 오류의 원문이나 API 키를 화면에 출력하지 않습니다.

**AI는 서류를 결정하지 않습니다.** 연구 설명에서 사실과 근거 구절을 제안하고, 사용자가 승인한 값만 규칙에 반영합니다. 기존 객관식 답변과 충돌하면 자동 덮어쓰기를 막습니다. 실제 외부 API 호출은 이 초기 개발 검증에 포함되지 않았으며, 연결 코드는 모의 응답으로 검증했습니다.

`.env`는 Git에 포함되지 않습니다. 연구 설명에 실제 이름, 전화번호, 참가자 응답, 비공개 연구 원문을 넣지 마세요. AI 기능을 선택할 때 설명이 외부 API로 전송됩니다.

## 화면 흐름

1. **기본 입력:** 기관, 신규심의 여부, 성인 여부, 방법, 동의 경로, 연구자 조건
2. **사실 확인:** 객관식 답변 검토, AI 제안 승인 또는 수정
3. **추가 확인:** 직접 식별정보, 연구 내용, 모집과 보상, 플랫폼과 연결키, 목록 점검
4. **준비 목록:** 조건별 필요 여부와 근거, 기관에 문의할 항목, 준비 상태, 보고서

추가 질문은 묶음별로 여러 세부 항목을 포함합니다. 두 차례를 모두 거치지 않고 중간에 결과를 볼 수도 있습니다. “아직 모름”을 선택한 답은 반복해서 묻지 않습니다.

## 코드와 개발 계획

| 위치 | 내용 |
|---|---|
| `app.py` | Streamlit 사용자 화면 |
| `src/agent/api.py` | `start`, `confirm`, `rejudge`, `revise`, `result` |
| `src/agent/engine.py` | 3값 규칙 판단, 범위 확인, 추가 질문 선택 |
| `src/agent/llm.py` | 선택적 AI 사실 추출과 응답 검증 |
| `src/agent/report.py` | 결과 데이터와 보고서 생성 |
| `data/` | 기관, 공식 출처, 질문, 규칙 JSON |
| `tests/` | 규칙, 상태 전이, AI 실패, 화면 흐름 테스트 |
| `scripts/evaluate.py` | 합성 사례 회귀 검증 |
| [제품 기획](docs/PRODUCT.md) | 목적, 입력과 출력, 사용 흐름, 지원 범위 |
| [구조와 인터페이스](docs/ARCHITECTURE.md) | 상태 전이와 코드 연결 방법 |
| [데이터와 검증](docs/DATA_AND_VALIDATION.md) | 수집 항목, 규칙 관리, 검증 지표 |
| [개발 계획](docs/DEVELOPMENT_PLAN.md) | 현재 완료 항목과 다음 작업의 완료 기준 |

## 테스트

Windows:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe scripts/evaluate.py
```

macOS / Linux:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest
.venv/bin/python scripts/evaluate.py
```

GitHub Actions에서도 같은 검증을 실행합니다. `tests/fixtures/regression_cases.json`의 10개 사례는 개발자가 구성한 합성 회귀 사례입니다. 실제 IRB 업무 정확도나 전문가 검증 성능을 의미하지 않습니다.

## 데이터의 현재 상태

공식 페이지 확인일은 **2026-09-30 UTC**입니다. 가톨릭대의 2026-09-29 공지와 2024년 표기의 일반 안내는 버전이 달라 조건부 서류 일부를 확인 필요로 남겼습니다. 서울교대 공개 안내에서 구체적 적용 조건이 없는 항목도 확정하지 않습니다.

출처 확인 후 30일이 지나면 결과를 확인 필요로 낮춥니다. 이는 앱의 재검토 정책이며 기관 규정상 유효기간이 아닙니다. 앱이 웹을 자동 조회하거나 최신 서식을 보장하지는 않습니다. 출처를 실제 재검토한 뒤에만 확인일을 수정하세요.

현재 **파일 업로드, 서명 검사, 문서 내용의 완전성 검사, 자동 제출, 서식 자동 작성, 실시간 공지 수집은 구현하지 않았습니다.** 준비 상태는 사용자가 표시한 값입니다. 기관별 추가 서류가 있을 수 있으므로 미확인 항목과 공식 출처를 함께 확인해야 합니다.
