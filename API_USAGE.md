# SMINFO 기업 정보 조회 API 사용 가이드

## 1. 개요

본 프로젝트는 SMINFO (중소기업현황정보시스템) 웹사이트에서 기업 정보를 크롤링하여, 사업자등록번호를 기반으로 해당 기업의 기본 정보 및 최근 3년간의 재무 정보(매출액, 영업이익)를 제공하는 FastAPI 애플리케이션입니다.

## 2. 환경 설정

### 2.1. 필수 환경 변수 (`.env` 파일)

프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 다음 환경 변수를 설정해야 합니다.

```env
# SMINFO 로그인 정보
SMINFO_ID="your_sminfo_id"
SMINFO_PW="your_sminfo_password"

# API 서버 설정 (선택 사항, 기본값 사용 가능)
# API_HOST="0.0.0.0"
# API_PORT="8000"

# HTML 스냅샷 저장 여부 및 경로 (선택 사항, 디버깅용)
# SAVE_HTML_SNAPSHOTS="True" 
# HTML_SNAPSHOT_BASE_PATH="collected_data/html_snapshots" 
```

*   `SMINFO_ID`: SMINFO 웹사이트 로그인 아이디
*   `SMINFO_PW`: SMINFO 웹사이트 로그인 비밀번호
*   `API_HOST` (선택): API 서버 호스트 (기본값: `0.0.0.0`)
*   `API_PORT` (선택): API 서버 포트 (기본값: `8000`)
*   `SAVE_HTML_SNAPSHOTS` (선택): 크롤링 과정 중 HTML 스냅샷 저장 여부 (`True` 또는 `False`, 기본값: `True`). 디버깅에 유용합니다.
*   `HTML_SNAPSHOT_BASE_PATH` (선택): 스냅샷 저장 기본 경로 (기본값: `collected_data/html_snapshots`)

### 2.2. Python 가상 환경 및 의존성 설치

1.  Python 3.10 이상 환경을 권장합니다.
2.  프로젝트 루트에서 가상 환경을 생성하고 활성화합니다.
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # macOS/Linux
    # .venv\Scripts\activate  # Windows
    ```
3.  필요한 라이브러리를 설치합니다.
    ```bash
    pip install -r requirements.txt
    ```
4.  Playwright 브라우저 드라이버를 설치합니다.
    ```bash
    playwright install
    ```

## 3. API 서버 실행 방법

프로젝트 루트 디렉토리에서 다음 명령어를 사용하여 FastAPI 서버를 실행합니다.

```bash
python -m uvicorn src.main:app --host <호스트 주소> --port <포트 번호> --reload
```

예시 (기본 설정 사용):
```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```
`--reload` 옵션은 코드 변경 시 서버를 자동으로 재시작하여 개발에 유용합니다.

서버가 정상적으로 실행되면 `http://<호스트 주소>:<포트 번호>/docs` 로 접속하여 Swagger UI를 통해 API 문서를 확인할 수 있습니다. (예: `http://localhost:8000/docs`)

## 4. 엔드포인트 명세

### GET `/api/v1/company-financials/{business_registration_number}`

지정된 사업자등록번호에 해당하는 기업의 기본 정보 및 재무 정보를 SMINFO에서 조회하여 반환합니다.

*   **Path Parameter**:
    *   `business_registration_number` (string, **필수**): 조회할 기업의 사업자등록번호. 하이픈(-)은 포함하거나 제외할 수 있습니다 (예: `123-45-67890` 또는 `1234567890`).

*   **성공 응답 (200 OK)**:
    ```json
    {
      "business_registration_number": "1448121513",
      "company_name": "(주)티오리한국",
      "ceo": "최시원",
      "status": "정상",
      "financials": {
        "2023_revenue": 19580873000.0,
        "2023_operating_profit": -9948472000.0,
        "2022_revenue": 12998777000.0,
        "2022_operating_profit": -11244835000.0,
        "2021_revenue": 7072655000.0,
        "2021_operating_profit": -5494677000.0
      }
    }
    ```

*   **주요 오류 응답**:
    *   **400 Bad Request**: 사업자등록번호 형식이 유효하지 않은 경우.
        ```json
        {
          "detail": "유효하지 않은 사업자등록번호 형식입니다: '123'. 형식: 000-00-00000 또는 0000000000"
        }
        ```
    *   **404 Not Found**: SMINFO에서 해당 사업자등록번호로 기업 정보를 찾을 수 없는 경우 (검색 결과 없음, 또는 스크래핑 과정에서 최종적으로 정보가 없다고 판단될 때).
        ```json
        {
          "detail": "사업자등록번호 '0000000000'으로 SMINFO에서 기업을 찾을 수 없었습니다."
        }
        ```
    *   **500 Internal Server Error**: 크롤링 중 예상치 못한 오류 발생 등 서버 내부 오류.
        ```json
        {
          "detail": "기업 정보 조회 중 오류 발생: [오류 메시지]. 잠시 후 다시 시도해주세요."
        }
        ```
    *   **503 Service Unavailable**: SMINFO 서비스 로그인 실패 또는 일시적 사용 불가 상태일 경우.
        ```json
        {
          "detail": "SMINFO 서비스 로그인 실패: [로그인 실패 상세 메시지]"
        }
        ```

## 5. 응답 데이터 (`CompanyFinancialsResponse`) 상세

| 필드명                           | 타입          | 설명                                                                                                | 비고                                     |
| -------------------------------- | ------------- | --------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| `business_registration_number` | string        | 사업자등록번호 (하이픈 없이 10자리)                                                                     |                                          |
| `company_name`                 | string / null | 회사명                                                                                              | 정보가 없거나 미확인 시 `null` 또는 "미확인(...)" |
| `ceo`                            | string / null | 대표자명                                                                                            | 정보가 없을 시 `null`                     |
| `status`                         | string        | 데이터 조회 상태. 아래 "`status` 필드 상세" 참고.                                                        |                                          |
| `financials`                     | object / null | 재무 정보 딕셔너리. 최근 3개년에 대한 매출액 및 영업이익. 키는 `YYYY_revenue`, `YYYY_operating_profit` 형식. | 재무정보가 없으면 빈 객체 `{}`            |

### 5.1. `status` 필드 상세

`status` 필드는 데이터 조회 및 처리 과정의 상태를 나타냅니다. 주요 값은 다음과 같습니다:

*   `"정상"`: 모든 정보가 정상적으로 조회된 경우.
*   `"정보없음"`: SMINFO에 해당 기업 정보 자체가 없거나, 재무 정보 등이 없는 경우. 세부 내용은 다음과 같이 접두사로 구분될 수 있습니다.
    *   `"정보없음 (검색결과없음)"`: 사업자번호로 검색 시 결과가 없는 경우.
    *   `"정보없음 (검색결과 링크 없음)"`: 검색 결과는 있으나 상세 정보 링크를 찾지 못한 경우.
    *   `"정보없음 (재무테이블 부재)"`: 재무 정보 테이블을 찾지 못한 경우.
    *   `"정보없음 (재무)"`: 재무 정보가 없는 경우 (대표자명 등은 있을 수 있음).
*   `"비공개"`: SMINFO에서 해당 기업 정보가 비공개 처리된 경우 (예: "정보 비공개" 팝업 발생).
*   `"오류 (...)"`: 크롤링 또는 데이터 처리 중 특정 오류가 발생한 경우. 괄호 안에 간략한 원인이 포함될 수 있습니다. (예: `"오류 (BRN 없음)"`, `"오류 (정보추출중)"`, `"오류 (상세페이지 로드 실패)"`)

### 5.2. `financials` 필드 구조

`financials` 객체는 연도별 매출액과 영업이익 정보를 담고 있습니다. 값의 단위는 **원** 입니다.

예시:
```json
{
  "2023_revenue": 202558709000.0,          // 2023년 매출액 (원)
  "2023_operating_profit": 18426808000.0,  // 2023년 영업이익 (원)
  "2022_revenue": 169069709000.0,
  "2022_operating_profit": 12622709000.0,
  "2021_revenue": 114417801000.0,
  "2021_operating_profit": -10663284000.0  // 음수일 경우 손실
}
```
SMINFO에서 제공하는 데이터의 단위가 "천원"이므로, API 응답에서는 이를 "원" 단위로 변환하여 제공합니다.

## 6. 주의사항 및 제약조건

*   **SMINFO 웹사이트 의존성**: 본 API는 SMINFO 웹사이트의 HTML 구조 및 로그인 방식에 의존적입니다. SMINFO 웹사이트가 변경될 경우 크롤러 코드 (주로 `src/crawler/scraper.py` 및 `src/crawler/config.py`의 선택자) 수정이 필요할 수 있습니다.
*   **IP 차단 가능성**: 과도하고 빈번한 API 요청은 대상 웹사이트의 정책에 따라 IP 차단 등의 제재를 받을 수 있습니다. API 사용 시 적절한 요청 간격을 유지하는 것이 좋습니다.
*   **Headless 브라우저 동작**: Headless 브라우저 환경에서는 일반 브라우저와 동작이 미묘하게 다를 수 있어, 간헐적인 로그인 불안정성이나 크롤링 실패가 발생할 수 있습니다. 현재 `LoginManager`에는 재시도 로직 및 서비스 접근을 통한 검증 로직이 포함되어 이러한 불안정성을 완화하려고 시도합니다.
*   **데이터 정확성**: 제공되는 데이터는 SMINFO 웹사이트에서 크롤링한 정보이며, 데이터의 완전성이나 절대적인 정확성을 보장하지는 않습니다.

## 7. 문제 해결 가이드 (간단히)

*   **로그인 실패 (503 오류)**:
    *   `.env` 파일에 `SMINFO_ID`와 `SMINFO_PW`가 정확히 설정되었는지 확인합니다.
    *   SMINFO 웹사이트에서 직접 로그인이 가능한지 확인합니다 (사이트 점검, 계정 문제 등).
*   **특정 기업 조회 실패 (404 또는 500 오류)**:
    *   `SAVE_HTML_SNAPSHOTS`를 `True`로 설정하고 API를 호출하면, `collected_data/html_snapshots/{사업자등록번호}/` 경로에 크롤링 과정 중의 HTML 스냅샷이 저장됩니다. 이 파일을 분석하면 오류 원인 파악에 도움이 될 수 있습니다.
    *   FastAPI 서버 로그를 확인하여 구체적인 오류 메시지나 크롤링 단계를 확인합니다.
*   **선택자(Selector) 문제**: SMINFO 웹사이트 구조 변경으로 인해 특정 요소(버튼, 테이블 등)를 찾지 못하는 경우, `src/crawler/config.py`의 CSS 선택자들을 수정해야 할 수 있습니다.

---

이 가이드가 API 사용에 도움이 되기를 바랍니다. 