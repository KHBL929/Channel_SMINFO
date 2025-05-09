# 중소기업 현황정보 크롤러 및 API 개발 PRD

## 1. 문서 개요

- **프로젝트명**: 중소기업 현황정보 크롤러 및 API 서비스 (Playwright, FastAPI 기반)
- **작성일**: 2025-05-09
- **문서 버전**: 1.4 (FastAPI API 기능 추가 및 상세 요구사항 보강)
- **목표**: 중소기업 현황정보 시스템(SMINFO)에서 자동 로그인 및 특정 조건의 기업 정보를 브라우저 자동화를 통해 수집하고, 수집된 주요 재무 정보(매출액, 영업이익)를 FastAPI 기반 API로 제공하는 시스템 개발.

## 2. 프로젝트 배경 및 목표

### 2.1. 배경

- 중소기업 현황정보 시스템(SMINFO)은 JavaScript 기반의 동적 웹사이트로, 단순 HTTP 요청만으로는 모든 정보에 접근하기 어려울 수 있음.
- 안정적인 데이터 수집 및 로그인 처리를 위해 실제 브라우저 환경을 제어하는 방식이 필요함.
- 특정 조건에 해당하는 기업 목록 및 상세 정보를 자동화된 방식으로 추출할 필요가 있음.
- 추출된 기업의 핵심 재무 정보를 외부 시스템에서 실시간으로 조회하고 활용할 수 있는 표준화된 인터페이스가 필요함.

### 2.2. 목표

- Playwright를 사용하여 SMINFO 웹사이트에 **자동으로 로그인** 수행.
- 로그인된 세션을 유지하며, 지정된 검색 조건(회사명 또는 사업자등록번호)에 맞는 기업 목록 및 **상세 정보(기본 정보, 특정 연도별 매출 현황 등)** 를 크롤링.
- 웹사이트의 페이지네이션(Pagination) 기능을 고려하여 모든 관련 페이지의 데이터 수집.
- 웹사이트의 크롤링 방어 정책(예: 요청 빈도 제한)을 준수하여 안정적인 데이터 수집.
- 수집된 데이터를 사용자가 활용하기 용이한 형태로 저장 (API 응답 형식 고려).
- **(신규)** FastAPI를 활용하여, 사업자등록번호를 입력받아 해당 기업의 **2022년, 2023년, 2024년 (또는 가용한 최신 3개년) 매출액 및 영업이익 정보**를 외부 시스템에서 실시간으로 조회할 수 있는 API 엔드포인트 제공.

## 3. 기능 요구사항

### 3.1. 필수 기능 (크롤러)

- **FR-001: 브라우저 자동화 기반 사용자 인증 및 세션 관리 (`login.py` 기반)**
    - Playwright를 사용하여 SMINFO 웹사이트에 자동 로그인할 수 있어야 한다.
    - **세부사항**:
        - `BrowserManager`를 통해 Playwright `Page` 객체 확보.
        - 메인 페이지 접속 -> 로그인 버튼 클릭 -> 로그인 페이지 이동.
        - 설정(`Config`) 파일에서 ID/PW를 로드하여 로그인 폼에 자동 입력 및 제출.
        - 로그인 성공/실패 여부 확인 (예: 로그아웃 버튼 존재 유무).
        - `is_logged_in` 상태 플래그 관리 및 로깅.
- **FR-002: 기업 검색 수행 (회사명 또는 사업자등록번호 기반) (`scraper.py - search_company` 기반)**
    - 로그인된 `Page` 객체를 사용하여, 제공된 회사명 또는 사업자등록번호로 웹사이트 내 검색 기능을 실행할 수 있어야 한다.
    - **세부사항**:
        - 검색어 입력 필드 (`#searchTxt` 또는 유사 선택자)에 회사명 또는 사업자등록번호 입력.
        - 검색 유형(회사명/사업자번호) 선택 로직 (필요시).
        - 검색 버튼 (`#searchBtn` 또는 유사 선택자) 클릭.
        - 검색 결과 페이지 로드 대기 (`networkidle`).
- **FR-003: 기업 기본 정보 추출 (`scraper.py - extract_company_info` 기반)**
    - 검색 결과 페이지에서 기업의 기본 정보(회사명, 대표자명, 사업자등록번호, 주소 등)를 추출할 수 있어야 한다.
    - **세부사항**:
        - 특정 테이블(`table.table_list`) 및 CSS 선택자를 사용하여 정보 추출.
- **FR-004: 기업 연도별 매출 현황 정보 추출 (`scraper.py - extract_financial_info` 기반)**
    - 기업 상세 정보 페이지 또는 검색 결과 내 "매출현황" 또는 유사 섹션에서 **2022년, 2023년, 2024년 (또는 가용한 최신 3개년)** 의 매출액, 영업이익 데이터를 추출할 수 있어야 한다.
    - **세부사항**:
        - Playwright로 페이지 컨텐츠를 가져온 후, `BeautifulSoup`으로 HTML 파싱.
        - "매출현황 정보가 없습니다." 또는 유사 메시지 처리.
        - 연도별 매출액, 영업이익 숫자 데이터 정제 (쉼표 제거, 단위 변환 등).
        - 추출된 데이터는 API 응답 형식을 고려하여 구조화 (예: `{'2022_revenue': 값, '2022_operating_profit': 값, ...}`).
        - **(신규) 재무 정보 페이지 HTML 저장**:
            - 데이터 추출을 시도한 기업의 재무 정보가 포함된 페이지(또는 재무 정보 테이블을 포함한 주요 영역)의 HTML 소스 코드를 로컬 파일 시스템에 저장한다.
            - **저장 시점**: 해당 기업의 재무 정보 페이지에 성공적으로 접근하여 크롤링을 시도하는 시점 (데이터 존재 유무와 관계없이 페이지 접근 시).
            - **저장 경로 (예시)**: `collected_data/html_snapshots/{사업자등록번호}/`
            - **파일명 (예시)**: `{YYYYMMDDHHMMSS}_financial_page.html` (타임스탬프를 포함하여 동일 기업 조회 시 여러 버전 저장 가능)
            - **목적**: 크롤링된 데이터의 검증, 웹사이트 UI 변경 추적, 에러 발생 시 원본 데이터 및 페이지 구조 확인을 통한 디버깅 지원.
            - 이 기능은 설정 파일(`Config` 또는 `.env`)을 통해 활성화/비활성화할 수 있도록 고려한다 (예: `SAVE_HTML_SNAPSHOTS=True`).
- **FR-005: 페이지네이션 처리**
    - **목표**: 검색 결과가 여러 페이지에 걸쳐 있을 경우, 다음 페이지로 이동하며 FR-003, FR-004를 반복 수행.
    - **접근 방안**:
        - SMINFO 검색 결과 페이지의 페이지네이션 UI 요소(예: '다음 페이지' 버튼, 페이지 번호 링크)의 CSS 선택자 또는 XPath를 식별한다.
        - '다음 페이지' 버튼의 활성화/비활성화 상태 또는 클래스 변화를 통해 마지막 페이지 여부를 판단한다.
        - 또는, 현재 페이지 번호와 전체 페이지 번호를 비교하여 반복 종료 조건을 설정한다. (웹사이트가 전체 페이지 정보를 제공하는 경우)
        - 각 페이지 이동 후, 컨텐츠가 완전히 로드될 때까지 적절한 대기(`wait_for_selector`, `wait_for_load_state`)를 적용한다.
- **FR-006: 데이터 출력/저장 (크롤러 실행 시)**
    - (선택 사항) 크롤러 직접 실행 시, 추출된 기업 정보를 화면에 출력하거나, 구조화된 데이터(예: 리스트, 딕셔너리, CSV)로 반환/저장.
- **FR-007: 요청 빈도 제어 및 안정성 확보**
    - Playwright의 내장 대기 기능 (`wait_for_load_state`, `wait_for_selector`, `wait_for_timeout`)을 적극 활용.
    - 필요한 경우 명시적인 `time.sleep()` 추가하여 서버 부하 감소 및 차단 방지.

### 3.2. 필수 기능 (FastAPI API)

- **FR-008: 사업자등록번호 기반 기업 재무 정보 조회 API 엔드포인트**
    - FastAPI를 사용하여 특정 기업의 연도별 재무 정보를 조회할 수 있는 API 엔드포인트를 제공해야 한다.
    - **세부사항**:
        - **HTTP Method**: `GET`
        - **Endpoint URL**: `/api/v1/company-financials/{business_registration_number}`
        - **경로 매개변수 (Path Parameter)**:
            - `business_registration_number` (str): 조회할 기업의 사업자등록번호 (하이픈 포함 또는 미포함 가능하도록 처리 권장).
        - **요청 본문 (Request Body)**: 없음.
        - **성공 응답 (Success Response - 200 OK)**:
            - Content-Type: `application/json`
            - Body 예시 (2022, 2023, 2024년 데이터가 모두 있는 경우):
              ```json
              {
                "business_registration_number": "123-45-67890",
                "company_name": "주식회사 예시", // (선택 사항, 크롤링 가능 시)
                "data_available_years": ["2022", "2023", "2024"], // 실제 데이터가 있는 연도 목록
                "financials": {
                  "2024_revenue": 1200000000,
                  "2024_operating_profit": 120000000,
                  "2023_revenue": 1100000000,
                  "2023_operating_profit": 110000000,
                  "2022_revenue": 1000000000,
                  "2022_operating_profit": 100000000
                }
              }
              ```
            - Body 예시 (일부 연도 데이터만 있는 경우 또는 특정 연도 데이터가 없는 경우 `null` 또는 해당 키 생략):
              ```json
              {
                "business_registration_number": "123-45-67890",
                "company_name": "주식회사 다른예시",
                "data_available_years": ["2023"],
                "financials": {
                  "2023_revenue": 900000000,
                  "2023_operating_profit": 80000000
                }
              }
              ```
        - **오류 응답 (Error Responses)**:
            - `400 Bad Request`: 사업자등록번호 형식이 유효하지 않거나, 필수 값이 누락된 경우.
            - `404 Not Found`: 해당 사업자등록번호로 기업 정보를 찾을 수 없거나, SMINFO에서 관련 재무 정보를 찾을 수 없는 경우.
            - `500 Internal Server Error`: 서버 내부 오류 (크롤링 엔진 실패, SMINFO 웹사이트 응답 오류 등).
            - `503 Service Unavailable`: SMINFO 웹사이트 점검 또는 일시적 장애로 크롤링 불가능한 경우.
    - **로직**:
        - API 요청 수신 시, `business_registration_number`를 정규화 (예: 하이픈 제거).
        - `LoginManager`를 통해 SMINFO 로그인 세션 확보 (필요시).
        - `Scraper` 모듈을 사용하여 `business_registration_number`로 SMINFO 웹사이트에서 해당 기업의 2022년, 2023년, 2024년 (또는 가용한 최신 3개년) 매출액과 영업이익을 크롤링 (FR-002, FR-004 로직 활용/확장).
        - 크롤링된 데이터를 가공하여 지정된 JSON 형식으로 응답.
        - (고려사항) 응답 속도 향상 및 SMINFO 서버 부하 감소를 위해, 요청 시마다 실시간 크롤링하는 대신 주기적으로 데이터를 크롤링하여 내부 DB에 캐싱/저장하고, API는 이 DB를 조회하는 방식 고려. 이 경우, 데이터의 최신성(freshness) 수준과 업데이트 주기를 명시해야 함. 현재는 실시간 크롤링을 기본으로 가정.

### 3.3. 선택/확장 기능

- **FR-009: 다양한 검색 조건 지원 (크롤러)**: FR-002 외 다른 기준으로 검색 기능 확장.
- **FR-010: 설정 파일 상세화 (`Config` 클래스 확장)**: URL, CSS 선택자, 대기 시간, 로그인 정보, API 포트 등을 설정 파일에서 관리.
- **FR-011: 에러 처리 및 로깅 강화**: Playwright `TimeoutError` 등 특정 예외 처리, API 요청/응답 상세 로깅 추가.
- **FR-012: `BrowserManager` 구체화 (`browser.py` 역할 정의)**
    - **핵심 책임**: Playwright 브라우저 인스턴스의 생명주기(시작, 종료)를 관리하고, 설정(headless 모드, user-agent, viewport 등)하며, 새로운 `Page` 객체를 생성하여 애플리케이션의 다른 부분(예: `LoginManager`, `Scraper`)에 제공한다.
    - **주요 인터페이스(메서드 예시)**:
        - `async def launch_browser() -> Page`: 브라우저를 시작하고 새 페이지를 반환.
        - `async def close_browser()`: 사용 중인 모든 페이지와 브라우저를 닫음.
        - `async def new_page() -> Page`: (필요시) 현재 브라우저 컨텍스트에서 새 페이지를 생성하여 반환.
    - `async with` 구문을 지원하여 자원(브라우저)의 자동 시작 및 정리(`__aenter__`, `__aexit__`)를 보장해야 한다.
    - 브라우저 종류(Chromium, Firefox, WebKit)를 선택할 수 있는 옵션을 제공할 수 있다 (설정 파일 연동).
- **FR-013: API 요청/응답 데이터 모델링 (Pydantic)**: FastAPI에서 Pydantic 모델을 사용하여 요청 파라미터 유효성 검사 및 응답 데이터 직렬화/구조화.
- **FR-014: API 인증/인가**: (필요시) API 키 기반 인증 또는 기타 보안 메커니즘 도입.
- **FR-015: 데이터 캐싱 전략 구현**: API 응답 속도 개선 및 SMINFO 서버 부하 감소를 위한 데이터 캐싱 메커니즘 도입 (예: Redis, 인메모리 캐시).

## 4. 비기능 요구사항

- **NFR-001: 안정성**: 브라우저 자동화 및 API 서비스 과정에서 발생할 수 있는 예외를 적절히 처리하여 시스템이 비정상 종료되지 않도록 한다.
- **NFR-002: 유지보수성**: 웹사이트 UI 변경 및 API 요구사항 변경에 유연하게 대응할 수 있도록 코드의 모듈성 및 가독성 확보. 선택자 정보는 별도 관리 (예: `Selector.md`, 설정 파일).
- **NFR-003: 사용성**: 크롤러 스크립트 실행 및 API 엔드포인트 사용이 용이해야 한다. API 문서는 자동으로 생성되거나 (예: FastAPI Swagger/ReDoc) 별도로 제공되어야 한다.
- **NFR-004: 보안**: 로그인 계정 정보와 같은 민감 정보는 프로젝트 루트의 `.env` 파일에 저장하고, 이 파일은 `.gitignore`에 추가하여 코드 저장소(GitHub 등)에 커밋되지 않도록 해야 한다. 애플리케이션은 이 `.env` 파일에서 설정을 로드한다. API 키 등 추가적인 민감 정보도 동일한 방식으로 관리한다.
- **NFR-005: API 응답 시간**: (목표) 사업자등록번호로 재무 정보 조회 API 호출 시, 평균 5초 이내 응답 (네트워크 및 SMINFO 웹사이트 응답 속도에 따라 변동 가능, 캐싱 미적용 시).
- **NFR-006: API 동시성**: (목표) 최소 10 TPS (Transactions Per Second) 처리 가능 (서버 사양 및 SMINFO 크롤링 정책에 따라 제한될 수 있음).
- **NFR-007: 확장성**: 향후 다른 종류의 기업 정보 추가 또는 다른 데이터 소스 연동 시 시스템 확장이 용이하도록 설계.

## 5. 기술 스택

- **프로그래밍 언어**: Python 3
- **주요 라이브러리**:
    - `Playwright`: 브라우저 자동화 (핵심)
    - `BeautifulSoup4`: HTML 파싱 (보조)
    - `FastAPI`: API 프레임워크 (신규)
    - `Uvicorn`: ASGI 서버 (FastAPI 실행용) (신규)
    - `Pydantic`: 데이터 유효성 검사 및 설정 관리 (FastAPI와 함께 사용)
    - `logging` (내장): 로깅
    - `python-dotenv`: 환경 변수 관리
    - `pandas` (선택): 데이터 처리 및 파일 저장 (주로 크롤러 직접 실행 시)
- **설정 관리**: Python 클래스(`Config`) 또는 외부 파일 (`.env`, `.ini`, `.yaml`)

## 6. 시스템 구성 요소 (제공된 파일 및 신규 컴포넌트 기반)

- **`BrowserManager` (`browser.py`에서 구현 예정)**: Playwright 브라우저 인스턴스 및 페이지 객체 생성, 관리.
- **`LoginManager` (`login.py`)**: `BrowserManager`를 통해 얻은 페이지 객체로 로그인/로그아웃 및 상태 확인.
- **`Scraper` (`scraper.py`)**: 로그인된 페이지 객체를 사용하여 실제 데이터 검색 및 추출 로직 수행 (사업자등록번호 기반 검색 및 연도별 재무 정보 추출 기능 포함).
- **`Config` (`config.py`)**: 로그인 정보, URL, 선택자, API 설정 등 전반적인 설정 값 관리.
- **`(신규) FastAPI Application (e.g., `src/main.py` 또는 `src/app.py`)`**: FastAPI 앱 인스턴스, API 라우터 설정, 미들웨어 설정 등.
- **`(신규) API Routers (e.g., `src/api/endpoints/company.py`)`**: `/company-financials` 와 같은 특정 경로에 대한 요청 처리 로직 정의.
- **`(신규) API Schemas/Models (e.g., `src/api/schemas.py`)`**: Pydantic 모델을 사용하여 API 요청/응답 데이터 구조 정의 및 유효성 검사.

## 7. 프로젝트 디렉토리 구조 (예시)
```
sminfo_crawler/
├── docs/
│   ├── PRD.md
│   ├── Selector.md
│   ├── ARCHITECTURE.md
│   ├── SETUP_AND_RUN_GUIDE.md
│   └── TROUBLESHOOTING.md
├── src/
│   ├── api/                     # (신규) FastAPI 관련 모듈
│   │   ├── __init__.py
│   │   ├── endpoints/           # API 엔드포인트 라우터
│   │   │   ├── __init__.py
│   │   │   └── company.py       # 기업 정보 관련 API
│   │   ├── schemas.py           # Pydantic 스키마 (요청/응답 모델)
│   │   └── deps.py              # (선택) API 의존성 주입 함수들
│   ├── crawler/                 # 크롤링 관련 모듈
│   │   ├── __init__.py
│   │   ├── browser.py
│   │   ├── config.py            # 크롤러 및 전반적 설정
│   │   ├── login.py
│   │   └── scraper.py
│   ├── core/                    # (선택) 핵심 로직, 유틸리티 등
│   │   └── config_global.py     # (만약 config.py가 crawler에 특화된다면)
│   ├── main.py                  # FastAPI 애플리케이션 진입점
│   └── tests/                   # 테스트 코드
│       └── ...
├── .env.example               # 환경 변수 예시 파일
├── requirements.txt           # Python 의존성 목록
└── README.md                  # 프로젝트 개요 및 기본 안내
```

## 8. 실행 방법 및 의존성 관리
- **의존성 관리**: 프로젝트 루트의 `requirements.txt` 파일에 필요한 라이브러리 목록을 정의한다. (예: `playwright`, `beautifulsoup4`, `fastapi`, `uvicorn[standard]`, `python-dotenv`, `pydantic`).
    - 설치: `pip install -r requirements.txt`
    - Playwright 브라우저 드라이버 설치: `playwright install` (또는 `playwright install chromium`)
- **설정**: `.env` 파일 (또는 `config.py` 직접 수정)을 통해 SMINFO 로그인 계정 정보, API 실행 포트, 브라우저 옵션 등을 설정한다. `.env.example` 파일을 제공하여 필요한 환경 변수 목록을 안내한다.
- **API 실행 방법**: (예시) 프로젝트 루트에서 `uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload` 명령어로 FastAPI 애플리케이션 실행 (`src.main:app`은 `src/main.py` 파일 내 FastAPI 앱 인스턴스 이름이 `app`일 경우).
- **크롤러 직접 실행 방법**: (예시) `python -m src.some_crawler_script` (별도 실행 스크립트 필요 시).

## 9. 핵심 로직 흐름도 (API 요청 중심)
1.  **API 요청 수신 (`FastAPI Application` - `src/main.py`, `src/api/endpoints/company.py`)**:
    *   클라이언트로부터 `GET /api/v1/company-financials/{business_registration_number}` 요청 접수.
    *   경로 매개변수(`business_registration_number`) 추출 및 Pydantic 스키마를 통한 유효성 검사.
2.  **인증 및 세션 준비 (`LoginManager` - `src/crawler/login.py`)**:
    *   (필요시) `BrowserManager`를 통해 Playwright `Page` 객체 확보.
    *   SMINFO 사이트에 자동 로그인 수행 및 세션 유지. (세션이 이미 유효하면 이 단계 생략 가능)
3.  **데이터 크롤링 (`Scraper` - `src/crawler/scraper.py`)**:
    *   로그인된 `Page` 객체와 `business_registration_number`를 사용하여 SMINFO 웹사이트 검색.
    *   해당 기업의 상세 정보 페이지로 이동 (또는 검색 결과에서 직접 추출).
    *   2022년, 2023년, 2024년 (또는 가용한 최신 3개년) 매출액 및 영업이익 정보 추출 (FR-004).
    *   정보를 찾지 못하거나 오류 발생 시 적절한 예외 처리.
4.  **응답 데이터 가공 (`API Routers` / `Scraper`)**:
    *   추출된 재무 정보를 Pydantic 스키마(`src/api/schemas.py`)에 정의된 응답 형식에 맞게 가공.
    *   `company_name`, `data_available_years` 등 추가 정보 포함.
5.  **API 응답 전송 (`FastAPI Application`)**:
    *   가공된 JSON 데이터를 클라이언트에게 HTTP 200 OK 응답으로 전송.
    *   오류 발생 시 해당 HTTP 상태 코드(400, 404, 500 등)와 오류 메시지 전송.
6.  **(요청 처리 완료 후) 자원 정리 (`BrowserManager`)**:
    *   (요청마다 브라우저를 띄우고 닫는 경우 또는 애플리케이션 종료 시) Playwright 브라우저 페이지 및 인스턴스 정리. (효율성을 위해 브라우저 인스턴스를 재사용하는 전략 고려)

## 10. 제약 조건
- SMINFO 웹사이트의 이용 약관 및 robots.txt를 준수해야 한다.
- 과도한 요청으로 서버에 부하를 주지 않도록 API 요청 빈도 제한 또는 크롤링 간격 조절이 필요할 수 있다.
- 크롤링된 데이터의 사용은 저작권 및 개인정보보호 관련 법규를 준수해야 한다.
- SMINFO 웹사이트의 UI 변경 시 크롤러 코드(특히 선택자)의 수정이 필요할 수 있다.
- API를 통해 제공되는 정보는 SMINFO 웹사이트에 공개된 정보에 한정되며, 정보의 정확성 및 최신성은 SMINFO에 의존한다.
- 2024년 데이터는 연도 말 또는 다음 해 초에 제공될 수 있으므로, 데이터 부재에 대한 처리가 필요하다.

## 11. 향후 고려사항
- **비동기 처리**: Playwright 및 FastAPI의 비동기 기능을 최대한 활용하여 I/O 바운드 작업(네트워크 요청, 브라우저 자동화)의 효율성 증대.
- **백그라운드 작업 및 스케줄링**: 대량 데이터 수집 또는 주기적인 데이터 업데이트를 위해 Celery, APScheduler 등과 같은 백그라운드 작업 큐 및 스케줄러 도입 고려.
- **데이터베이스 연동**: 수집된 데이터를 RDBMS(PostgreSQL, MySQL) 또는 NoSQL(MongoDB)에 저장하여 API 응답 속도 개선 및 데이터 영속성 확보.
- **API 문서 자동화**: FastAPI의 자동 API 문서 생성 기능(Swagger UI, ReDoc)을 적극 활용하고, 필요한 경우 추가 설명 보강.
- **테스트 커버리지**: 단위 테스트, 통합 테스트, E2E 테스트 코드를 작성하여 시스템 안정성 및 신뢰성 확보.
- **모니터링 및 로깅**: Prometheus, Grafana 등을 이용한 시스템 모니터링 및 ELK Stack 등을 이용한 중앙화된 로깅 시스템 구축 고려.