# SMINFO 크롤러 및 API 서버 환경 설정 및 실행 가이드

**최종 업데이트:** (오늘 날짜로 가정, 실제 최종 수정일 반영 필요)

이 문서는 `sminfo_crawler` 프로젝트를 로컬 환경에서 설정하고 실행하는 방법을 안내합니다. 크롤러 단독 실행 및 FastAPI 기반 API 서버 실행 방법을 모두 포함합니다.

## 1. 사전 요구사항

-   **Python**: Python 3.8 이상 버전 설치를 권장합니다. (Playwright 및 FastAPI 호환성 고려)
    -   Python 설치 확인: `python --version` 또는 `python3 --version`
-   **pip**: Python 패키지 관리자. Python 설치 시 대부분 함께 설치됩니다.
    -   pip 설치 확인: `pip --version` 또는 `pip3 --version`

## 2. 프로젝트 클론 (또는 다운로드)

Git을 사용하는 경우:
```bash
git clone <저장소_URL>
cd sminfo_crawler
```
또는 프로젝트 파일을 직접 다운로드하여 원하는 디렉토리에 압축 해제합니다.

## 3. 가상 환경 설정 (권장)

프로젝트별 의존성 관리를 위해 가상 환경 사용을 강력히 권장합니다.

```bash
# 프로젝트 루트 디렉토리에서 실행
python -m venv venv
```

가상 환경 활성화:
-   Windows:
    ```bash
    .\venv\Scripts\activate
    ```
-   macOS/Linux:
    ```bash
    source venv/bin/activate
    ```
가상 환경이 활성화되면 프롬프트 앞에 `(venv)`가 표시됩니다.

## 4. 의존성 라이브러리 설치

프로젝트 실행에 필요한 Python 라이브러리들을 설치합니다. `requirements.txt` 파일이 프로젝트 루트에 제공되어야 합니다.

```bash
# (venv) 가상 환경이 활성화된 상태에서 실행
pip install -r requirements.txt
```

`requirements.txt` 파일에는 다음과 같은 주요 라이브러리가 포함되어야 합니다 (버전은 프로젝트에 맞게 명시):
-   `playwright`
-   `beautifulsoup4`
-   `fastapi` (신규)
-   `uvicorn[standard]` (FastAPI 실행을 위한 ASGI 서버, standard는 추가 기능 포함) (신규)
-   `pydantic` (FastAPI와 함께 데이터 유효성 검사 및 설정 관리에 사용)
-   `python-dotenv` (환경 변수 관리를 위해 `.env` 파일 사용 시 권장)
-   `pandas` (데이터 처리 및 저장 시, 선택 사항)

## 5. Playwright 브라우저 드라이버 설치

Playwright는 실제 브라우저를 제어하므로, 해당 브라우저의 드라이버(엔진)를 설치해야 합니다.

```bash
# (venv) 가상 환경이 활성화된 상태에서 실행
playwright install
```
위 명령은 Chromium, Firefox, WebKit 브라우저 엔진을 모두 설치합니다. 특정 브라우저만 설치하려면 (예: Chromium만):
```bash
playwright install chromium
```

## 6. 설정 파일 구성 (`config.py` 또는 `.env`)

SMINFO 웹사이트 로그인 정보, API 서버 설정 및 기타 설정을 구성해야 합니다. **가장 권장되는 방식은 `.env` 파일을 사용하는 것입니다.**

### `.env` 파일 사용 (강력 권장)

민감한 정보(예: 로그인 계정)를 코드와 분리하여 안전하게 관리하고, 다양한 환경(개발, 스테이징, 프로덕션)에 따라 설정을 쉽게 변경할 수 있도록 `.env` 파일을 사용하는 것이 가장 좋습니다.

1.  프로젝트 루트 디렉토리에 제공된 `.env.example` 파일을 복사하여 `.env` 파일을 생성합니다.
    ```bash
    cp .env.example .env
    ```
    (`.env.example` 파일이 없다면, 아래 내용을 참고하여 직접 `.env` 파일을 생성합니다.)

2.  생성된 `.env` 파일을 열어 실제 값을 입력합니다. **이 파일은 절대로 Git 저장소에 커밋해서는 안 됩니다.** (`.gitignore` 파일에 `.env`가 포함되어 있는지 확인하십시오.)
    ```env
    # SMINFO 크롤러 및 API 서버 설정

    # SMINFO 로그인 정보 (필수 - 실제 값으로 변경)
    SMINFO_USERNAME="실제_SMINFO_아이디"
    SMINFO_PASSWORD="실제_SMINFO_비밀번호"

    # 브라우저 실행 옵션 (선택 사항, 기본값 False)
    HEADLESS_BROWSER=False

    # FastAPI API 서버 설정 (선택 사항, 기본값 아래와 같음)
    API_HOST="0.0.0.0"
    API_PORT=8000

    # HTML 스냅샷 저장 기능 (선택 사항, 기본값 True)
    SAVE_HTML_SNAPSHOTS=True
    HTML_SNAPSHOTS_BASE_DIR="collected_data/html_snapshots"
    ```

3.  Python 코드 (예: `src/crawler/config.py` 또는 Pydantic `BaseSettings` 사용)에서는 `python-dotenv` 라이브러리나 Pydantic의 기능을 사용하여 이 `.env` 파일에서 환경 변수를 로드합니다.
    ```python
    # 예시: Pydantic BaseSettings 사용 시 (src/core/config.py 또는 유사 파일)
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        SMINFO_USERNAME: str
        SMINFO_PASSWORD: str
        HEADLESS_BROWSER: bool = False
        API_HOST: str = "0.0.0.0"
        API_PORT: int = 8000
        SAVE_HTML_SNAPSHOTS: bool = True
        HTML_SNAPSHOTS_BASE_DIR: str = "collected_data/html_snapshots"

        model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

    settings = Settings()
    ```

### (대안) `config.py` 파일 직접 수정 (덜 권장됨)

개발 초기 단계 또는 매우 간단한 경우, Python 설정 파일(`src/crawler/config.py` 등)에 직접 값을 입력할 수도 있습니다. 하지만 이 방법은 민감 정보가 코드에 포함될 수 있어 Git 커밋 시 각별한 주의가 필요하며, 일반적으로 권장되지 않습니다.

## 7. FastAPI API 서버 실행 (신규)

모든 설정이 완료되면, Uvicorn을 사용하여 FastAPI 애플리케이션을 실행합니다.
`src/main.py` 파일에 FastAPI 앱 인스턴스가 `app`으로 정의되어 있다고 가정합니다.

프로젝트 루트 디렉토리에서 다음 명령어를 사용하여 API 서버를 시작합니다:
```bash
# (venv) 가상 환경이 활성화된 상태에서 실행
# --reload 옵션은 개발 중 코드 변경 시 서버 자동 재시작 (프로덕션에서는 제거)
uvicorn src.main:app --host <API_HOST 값 또는 0.0.0.0> --port <API_PORT 값 또는 8000> --reload
```
예를 들어, `.env` 파일 또는 설정에 `API_HOST="0.0.0.0"`, `API_PORT=8000`로 설정된 경우:
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```
서버가 성공적으로 시작되면, 콘솔에 Uvicorn 관련 로그와 함께 애플리케이션 시작 메시지가 표시됩니다.

## 8. API 서버 동작 확인 (신규)

-   **자동 API 문서 (Swagger UI)**: 웹 브라우저를 열고 `http://<API_HOST>:<API_PORT>/docs` (예: `http://localhost:8000/docs` 또는 `http://127.0.0.1:8000/docs`)로 접속하면 FastAPI가 자동으로 생성해주는 대화형 API 문서를 확인할 수 있습니다. 여기서 API 엔드포인트를 직접 테스트해볼 수 있습니다.
-   **대안 API 문서 (ReDoc)**: `http://<API_HOST>:<API_PORT>/redoc` (예: `http://localhost:8000/redoc`)에서도 다른 스타일의 API 문서를 볼 수 있습니다.
-   **HTTP 클라이언트 도구**: Postman, Insomnia, curl 등의 HTTP 클라이언트 도구를 사용하여 정의된 API 엔드포인트(예: `GET /api/v1/company-financials/{business_registration_number}`)로 요청을 보내고 응답을 확인할 수 있습니다.

## 9. (선택 사항) 배치 크롤러 실행

API 서버와 별개로, 특정 조건에 따라 데이터를 일괄 수집하는 크롤러 스크립트가 있다면 해당 스크립트를 직접 실행할 수 있습니다.

(예시) `src/batch_crawler.py` (또는 기존 `src/main_test.py` 등) 스크립트가 프로젝트의 배치 크롤링 실행 파일이라고 가정합니다.

프로젝트 루트 디렉토리에서 다음 명령어를 사용하여 실행합니다:
```bash
# (venv) 가상 환경이 활성화된 상태에서 실행
python -m src.batch_crawler --some-argument value
```
실행 중에는 콘솔에 로깅 메시지가 출력됩니다. `config.py` (또는 `.env`)의 `HEADLESS_BROWSER` 설정을 `False`로 하면 브라우저가 실제로 동작하는 것을 볼 수 있습니다.

## 10. 크롤링 결과 확인

-   **API 호출 시**: HTTP 클라이언트 도구나 프로그래밍 방식으로 API를 호출하여 JSON 응답을 확인합니다.
-   **배치 크롤러 실행 시**: 스크립트의 구현에 따라 결과는 콘솔에 출력되거나, 지정된 파일(예: CSV, Excel)로 저장될 수 있습니다.
-   로그 파일이 생성되도록 설정했다면, 해당 파일에서 상세 실행 내역을 확인할 수 있습니다. 
-   **HTML 스냅샷 확인**: 만약 `SAVE_HTML_SNAPSHOTS` 설정이 `True`로 되어 있다면, `HTML_SNAPSHOTS_BASE_DIR` (기본값: `collected_data/html_snapshots`) 아래에 각 사업자등록번호별 폴더가 생성되고, 그 안에 타임스탬프가 찍힌 HTML 파일들이 저장됩니다. 이 파일들은 웹 브라우저로 열어 크롤링 시점의 페이지 내용을 확인할 수 있습니다.
-   **저장 공간 관리**: HTML 스냅샷 저장 기능은 디스크 공간을 점유할 수 있으므로, 특히 많은 기업을 대상으로 장기간 운영 시 주기적으로 오래된 파일을 정리하거나 백업하는 방안을 고려해야 합니다. 