# SMINFO 크롤러 및 API 서버 문제 해결 가이드

**최종 업데이트:** (오늘 날짜로 가정, 실제 최종 수정일 반영 필요)

이 문서는 `sminfo_crawler` 프로젝트 실행 중 발생할 수 있는 일반적인 문제들과 해결 방법을 안내합니다. 크롤러 단독 실행 및 FastAPI API 서버 관련 문제를 모두 다룹니다.

## 1. Playwright 크롤러 관련 문제

-   **문제**: `playwright._impl._api_types.Error: Executable doesn't exist at ...` 또는 브라우저 실행 관련 오류.
    -   **원인**: Playwright 브라우저 드라이버가 제대로 설치되지 않았거나 경로 문제가 있을 수 있습니다.
    -   **해결 방법**:
        1.  가상 환경이 활성화된 상태인지 확인합니다.
        2.  터미널에서 `playwright install` 또는 특정 브라우저(예: `playwright install chromium`)를 다시 실행하여 드라이버를 설치/업데이트합니다.
        3.  시스템 환경 변수 `PLAYWRIGHT_BROWSERS_PATH`가 올바르게 설정되어 있는지 확인하거나, Playwright가 기본 경로에 드라이버를 설치했는지 확인합니다. (일반적으로 `playwright install`로 해결됨)

-   **문제**: 스크립트 실행 시 `No module named 'playwright'` 오류.
    -   **원인**: `playwright` 라이브러리가 현재 Python 환경에 설치되지 않았습니다.
    -   **해결 방법**: `pip install playwright` 명령을 실행하여 라이브러리를 설치합니다. (`requirements.txt` 사용 시 `pip install -r requirements.txt`)

-   **문제**: 로그인 실패 (자세한 내용은 이전 `TROUBLESHOOTING.md`의 "2. 로그인 실패" 섹션 참조)
    -   **원인**: 아이디/비밀번호 오류, 웹사이트 UI 변경(선택자 불일치), CAPTCHA, 네트워크 문제 등.
    -   **해결 방법**: 설정값 확인, `HEADLESS_BROWSER = False`로 디버깅, 선택자 검증, CAPTCHA 확인, 네트워크 점검.

-   **문제**: 요소(Element)를 찾을 수 없음 (`TimeoutError` 등) (자세한 내용은 이전 `TROUBLESHOOTING.md`의 "3. 요소(Element)를 찾을 수 없음" 섹션 참조)
    -   **원인**: 잘못된 선택자, 페이지 로딩 지연, 동적 요소 미생성, 이전 단계(로그인 등) 실패.
    -   **해결 방법**: `HEADLESS_BROWSER = False`로 디버깅, 선택자 검증, Playwright 대기 기능 활용, 이전 단계 성공 여부 확인.

-   **문제**: 데이터 추출 실패 또는 빈 데이터 반환 (자세한 내용은 이전 `TROUBLESHOOTING.md`의 "4. 데이터 추출 실패" 섹션 참조)
    -   **원인**: 선택자 변경, 대상 데이터 부재, 파싱 로직 오류, 페이지네이션 오류.
    -   **해결 방법**: `HEADLESS_BROWSER = False`로 디버깅, 선택자/파싱 로직 검증, "정보 없음" 케이스 처리 확인, 페이지네이션 로직 점검.

-   **문제**: IP 차단 의심 (자세한 내용은 이전 `TROUBLESHOOTING.md`의 "5. IP 차단 의심" 섹션 참조)
    -   **원인**: 과도한 요청으로 인한 웹사이트 정책 위반.
    -   **해결 방법**: 요청 간 대기 시간 증가, 웹사이트 정책 준수.

## 2. FastAPI 및 Uvicorn 실행 관련 문제 (신규)

-   **문제**: API 서버 실행 시 `No module named 'fastapi'` 또는 `No module named 'uvicorn'`.
    -   **원인**: FastAPI 또는 Uvicorn 라이브러리가 현재 Python 환경에 설치되지 않았습니다.
    -   **해결 방법**: `pip install fastapi uvicorn` 또는 `pip install -r requirements.txt`를 실행하여 필요한 라이브러리를 설치합니다.

-   **문제**: Uvicorn 실행 시 `Error: [Errno 98] Address already in use` (Linux/macOS) 또는 유사한 포트 사용 중 오류 (Windows).
    -   **원인**: 다른 애플리케이션이 이미 해당 포트(예: 8000)를 사용 중입니다.
    -   **해결 방법**:
        1.  `uvicorn src.main:app --port <다른_포트번호>` 와 같이 다른 포트 번호를 지정하여 실행합니다.
        2.  또는, 해당 포트를 사용 중인 기존 프로세스를 찾아 종료합니다. (예: `lsof -i :<포트번호>` 후 `kill <PID>` (Linux/macOS), `netstat -ano | findstr :<포트번호>` 후 `taskkill /PID <PID> /F` (Windows))

-   **문제**: Uvicorn 실행 시 `Error loading ASGI app. Could not import module "src.main"` (또는 유사한 import 오류).
    -   **원인**:
        1.  FastAPI 애플리케이션 파일 경로(`src.main`)가 잘못되었거나, 해당 파일 내에 FastAPI 앱 인스턴스(예: `app = FastAPI()`) 이름이 Uvicorn 명령어에 지정된 이름(예: `:app`)과 다릅니다.
        2.  Python 모듈 검색 경로(`PYTHONPATH`) 문제 또는 오타.
    -   **해결 방법**:
        1.  Uvicorn 실행 명령어에서 모듈 경로와 FastAPI 앱 인스턴스 이름이 정확한지 확인합니다 (예: `uvicorn src.main:app`에서 `src/main.py` 파일 내 `app` 인스턴스 지칭).
        2.  프로젝트 루트 디렉토리에서 Uvicorn 명령을 실행하고 있는지 확인합니다.
        3.  필요시 `PYTHONPATH` 환경 변수를 확인하거나, 가상 환경이 올바르게 활성화되었는지 확인합니다.

## 3. API 호출 관련 문제 (신규)

-   **문제**: API 호출 시 `400 Bad Request` 응답.
    -   **원인**: 클라이언트 요청이 유효하지 않습니다. 경로 매개변수(예: 사업자등록번호)가 누락되었거나 형식이 잘못되었을 수 있습니다. FastAPI의 Pydantic 모델 유효성 검사에 실패했을 가능성이 높습니다.
    -   **해결 방법**:
        1.  API 요청 시 경로 매개변수나 요청 본문이 `PRD.md` 또는 FastAPI 자동 문서(`/docs`)에 정의된 형식과 일치하는지 확인합니다.
        2.  사업자등록번호의 형식이 올바른지 확인합니다.
        3.  서버 측 FastAPI 애플리케이션 로그에서 Pydantic 유효성 검사 오류 메시지를 확인합니다.

-   **문제**: API 호출 시 `404 Not Found` 응답.
    -   **원인**:
        1.  요청한 API 엔드포인트 URL이 잘못되었습니다 (오타 등).
        2.  (본 프로젝트의 경우) 제공된 사업자등록번호에 해당하는 기업 정보를 SMINFO 웹사이트에서 찾을 수 없거나, 크롤링 과정에서 관련 재무 정보를 수집하지 못한 경우.
    -   **해결 방법**:
        1.  API 엔드포인트 URL이 정확한지 다시 확인합니다 (`PRD.md` 또는 `/docs` 참조).
        2.  사업자등록번호가 올바른지, 해당 번호로 SMINFO에서 수동으로 조회가 가능한지 확인해봅니다.
        3.  서버 로그를 확인하여 크롤링 과정에서 특정 기업 정보를 찾지 못했다는 메시지가 있는지 확인합니다.

-   **문제**: API 호출 시 `500 Internal Server Error` 응답.
    -   **원인**: 서버 측 코드(FastAPI 애플리케이션, 크롤러 로직 등)에서 예기치 않은 오류가 발생했습니다.
    -   **해결 방법**:
        1.  서버(Uvicorn) 콘솔 로그 또는 별도의 로그 파일에서 상세한 오류 메시지(스택 트레이스 등)를 확인하여 문제의 원인을 파악합니다.
        2.  크롤러 로직(`scraper.py`, `login.py` 등)이나 API 라우터 핸들러(`src/api/endpoints/company.py` 등)의 코드에 버그가 있는지 검토합니다.

-   **문제**: API 호출 시 `503 Service Unavailable` 응답.
    -   **원인**: SMINFO 웹사이트가 점검 중이거나 일시적인 장애로 인해 크롤링이 불가능한 상태일 수 있습니다. 또는 크롤링 엔진 자체에 문제가 발생했을 수 있습니다.
    -   **해결 방법**:
        1.  SMINFO 웹사이트에 직접 접속하여 서비스 상태를 확인합니다.
        2.  잠시 후 다시 시도합니다.
        3.  서버 로그를 확인하여 크롤링 엔진 관련 오류 메시지가 있는지 확인합니다.

-   **문제**: API 응답 데이터가 예상과 다르거나, 특정 필드가 누락됨.
    -   **원인**:
        1.  크롤러가 SMINFO 웹사이트에서 데이터를 잘못 추출했거나, 일부 데이터가 없는 경우.
        2.  데이터 가공 로직 또는 FastAPI의 Pydantic 응답 스키마(`src/api/schemas.py`) 정의에 문제가 있을 수 있습니다.
    -   **해결 방법**:
        1.  `PRD.md`의 API 응답 명세와 실제 응답을 비교합니다.
        2.  `src/api/schemas.py`에 정의된 Pydantic 응답 모델이 의도한 대로 구성되어 있는지 확인합니다.
        3.  크롤러의 데이터 추출 및 가공 로직을 디버깅하여 데이터가 올바르게 처리되는지 확인합니다.
        4.  (신규) 만약 재무 정보 페이지 HTML 저장 기능이 활성화되어 있다면 (`PRD.md` FR-004 참조), 해당 기업의 사업자등록번호로 저장된 HTML 파일(예: `collected_data/html_snapshots/{사업자등록번호}/{타임스탬프}_financial_page.html`)을 열어 당시의 실제 페이지 내용을 확인합니다. 이를 통해 크롤러가 본 HTML과 실제 데이터를 비교하여 파싱 로직의 문제를 진단하거나, 웹사이트 UI 변경 여부를 확인할 수 있습니다.

## 4. 일반적인 디버깅 팁

-   **로깅 활용**: `logging` 모듈을 사용하여 스크립트 및 API 서버의 각 단계에서 어떤 일이 발생하는지 상세한 로그를 남깁니다. 로깅 레벨(INFO, DEBUG 등)을 조절하여 필요한 만큼의 정보를 얻습니다. FastAPI 요청/응답에 대한 로깅 미들웨어를 추가하는 것도 유용합니다.
-   **(신규) 저장된 HTML 스냅샷 활용**: 재무 정보 페이지 HTML 저장 기능이 활성화된 경우, 크롤링 시점의 원본 페이지 내용을 직접 확인함으로써 데이터 불일치 또는 파싱 오류의 원인을 파악하는 데 도움이 됩니다.
-   **Playwright Inspector 사용** (크롤러 디버깅 시):
    ```bash
    # 터미널에서 환경 변수 설정 후 스크립트 실행 (macOS/Linux)
    PWDEBUG=1 python -m src.your_crawler_script
    # (Windows PowerShell)
    # $env:PWDEBUG=1; python -m src.your_crawler_script
    ```
-   **`HEADLESS_BROWSER = False`** (크롤러 디버깅 시): 개발 및 디버깅 중에는 브라우저 창을 직접 보면서 문제를 파악하는 것이 매우 유용합니다.
-   **FastAPI/Uvicorn `--reload` 옵션**: 개발 중 API 서버 코드 변경 시 Uvicorn이 자동으로 재시작하도록 `--reload` 옵션을 사용합니다 (프로덕션 환경에서는 사용하지 않음).
-   **FastAPI 자동 문서 활용**: 웹 브라우저에서 `/docs` (Swagger UI) 또는 `/redoc` (ReDoc) 엔드포인트에 접속하여 API 명세를 확인하고, 직접 테스트 요청을 보내면서 디버깅할 수 있습니다.
-   **점진적 테스트**: 전체 시스템을 한 번에 테스트하기보다, 작은 단위(크롤러 모듈, API 엔드포인트 핸들러 등)로 나누어 각 부분이 정상 동작하는지 확인하며 개발합니다. 