import os
from dotenv import load_dotenv

# .env 파일이 있다면 로드합니다.
# 프로젝트 루트에 .env 파일을 생성하고 아래와 같이 환경 변수를 설정하세요.
# SMINFO_ID="your_sminfo_id"
# SMINFO_PW="your_sminfo_password"
# API_HOST="0.0.0.0"
# API_PORT="8000"
# SAVE_HTML_SNAPSHOTS="True" # 또는 "False"
# HTML_SNAPSHOT_BASE_PATH="collected_data/html_snapshots"
# SMINFO_BASE_URL="https://www.sminfo.go.kr" # 실제 SMINFO 사이트 주소
# SMINFO_LOGIN_URL="https://www.sminfo.go.kr/login.do" # 실제 SMINFO 로그인 페이지 주소 (변경될 수 있음)


# 프로젝트 루트 경로를 기준으로 .env 파일을 찾습니다.
# 이 config.py 파일은 src/crawler/ 내부에 위치하므로, 상위 디렉토리의 .env를 로드합니다.
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(dotenv_path=dotenv_path)

class Config:
    """
    애플리케이션 설정을 관리하는 클래스.
    환경 변수 또는 기본값을 사용하여 설정을 초기화합니다.
    """
    # SMINFO Login Credentials
    SMINFO_ID: str = os.getenv("SMINFO_ID", "default_id_please_change_in_env")
    SMINFO_PW: str = os.getenv("SMINFO_PW", "default_pw_please_change_in_env")

    # SMINFO URLs
    SMINFO_BASE_URL: str = os.getenv("SMINFO_BASE_URL", "https://sminfo.mss.go.kr/cm/sv/CSV001R0.do")
    SMINFO_LOGIN_URL: str = os.getenv("SMINFO_LOGIN_URL", "https://sminfo.mss.go.kr/cm/mm/CMM004R0.do") # 실제 URL 확인 필요

    # API Server Settings
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # Crawler Settings
    # SAVE_HTML_SNAPSHOTS는 문자열 "False"일 경우 False로, 그 외에는 True로 처리 (환경변수는 보통 문자열)
    SAVE_HTML_SNAPSHOTS: bool = os.getenv("SAVE_HTML_SNAPSHOTS", "True").lower() == "true"
    HTML_SNAPSHOT_BASE_PATH: str = os.getenv("HTML_SNAPSHOT_BASE_PATH", "collected_data/html_snapshots")
    SMINFO_MAIN_PAGE_URL: str = os.getenv("SMINFO_MAIN_PAGE_URL", "https://sminfo.mss.go.kr/cm/sv/CSV001R0.do")
    
    # Playwright Settings (예시, 필요시 추가)
    # BROWSER_TYPE: str = os.getenv("BROWSER_TYPE", "chromium")
    # HEADLESS_MODE: bool = os.getenv("HEADLESS_MODE", "True").lower() != "false"
    DEFAULT_SLEEP_TIME_SHORT: float = float(os.getenv("DEFAULT_SLEEP_TIME_SHORT", "0.5")) # 초 단위
    DEFAULT_SLEEP_TIME_VERY_SHORT: float = float(os.getenv("DEFAULT_SLEEP_TIME_VERY_SHORT", "0.2")) # 초 단위
    DEFAULT_SLEEP_TIME_MEDIUM: float = float(os.getenv("DEFAULT_SLEEP_TIME_MEDIUM", "1.5")) # 초 단위
    MAX_LOGIN_ATTEMPTS: int = int(os.getenv("MAX_LOGIN_ATTEMPTS", "3")) # 최대 로그인 시도 횟수

    # --- SMINFO 웹사이트 선택자 ---
    # 로그인 페이지
    LOGIN_ID_INPUT_SELECTOR: str = "#id"
    LOGIN_PW_INPUT_SELECTOR: str = "#pwd"
    LOGIN_BUTTON_SELECTOR: str = "#contents_sub > div:nth-child(3) > div > div.login_lr_box.clearfix > div.lr_text_r > div:nth-child(1) > form > button > span"
    LOGOUT_BUTTON_SELECTOR: str = "#main_link > div > div.main_login_box.m_main_login_box > div > form > fieldset > div > button > span" # 사용자 제공 최신 선택자로 업데이트
    MAIN_PAGE_LOGIN_LINK_SELECTOR: str = "#wrap > div.header.clearfix > div.global_box > ul > li:nth-child(2) > a:not([onclick*='fnLogout']) " # 메인 페이지의 로그인 링크 (공백 제거)

    # 기업 검색 페이지 (GSF002R0.print)
    SEARCH_PAGE_URL: str = "https://sminfo.mss.go.kr/gc/sf/GSF002R0.print"
    SEARCH_TEXT_INPUT_SELECTOR: str = "#searchTxt"
    SEARCH_BUTTON_SELECTOR: str = "#contents_sub > div:nth-child(3) > form:nth-child(5) > div > div.button_group > button.btn.btn_blue.ui-btn.ui-shadow.ui-corner-all > span"
    
    # 검색 결과 목록 테이블 (사업자등록번호 검색 시 결과가 하나라도 이 테이블을 거칠 수 있음)
    RESULTS_TABLE_SELECTOR: str = "#contents_sub > div:nth-child(3) > form:nth-child(5) > div > div.ova > table"
    # 검색 결과 목록에서 상세 페이지로 이동하는 링크 (첫 번째 결과 기준)
    SEARCH_RESULT_DETAIL_LINK_SELECTOR: str = "#contents_sub > div:nth-child(3) > form:nth-child(5) > div > div.ova > table > tbody > tr > td:nth-child(1) > a"

    # 기업 상세 정보 페이지 (IEI001R0.do)
    COMPANY_TITLE_SELECTOR: str = '#contents_sub > div:nth-child(3) > div > h4.table_title' # 회사명 표시 제목
    CEO_NAME_IN_DETAIL_PAGE_SELECTOR: str = 'table.col_table_mob td[headers="row02"]' # 대표자명

    # 재무 정보 테이블 (매출현황)
    FINANCIAL_TABLE_SELECTOR_BASE: str = "table.list_table.type02" # 기본 테이블 선택자
    FINANCIAL_TABLE_CAPTION_TEXT: str = "매출현황" # 테이블 캡션에 포함된 텍스트
    YEAR_ROW_SELECTOR: str = "tbody tr" # 재무 테이블 내 연도별 데이터 행
    # NO_FINANCIAL_DATA_MESSAGE_SELECTOR: str = "div.no_data_message_class" # 정보 없음 메시지 (현재 스냅샷에는 없음)

    # 페이지네이션 (현재는 사업자번호 검색만 사용하므로 직접 사용 안함, 필요시 주석 해제)
    # NEXT_PAGE_BUTTON_SELECTOR: str = "a.next_page_button_class"

    # CSS 선택자 (Selector.md 또는 실제 페이지 분석 기반)
    LOGIN_PAGE_URL_SUFFIX: str = os.getenv("LOGIN_PAGE_URL_SUFFIX", "/cm/mm/CMM004R0.do") # 로그인 페이지 경로 (메인에서 클릭 시 이동)

    SMINFO_LOGIN_PAGE_URL: str = f"{SMINFO_BASE_URL}/cm/mm/CMM004R0.do"
    SMINFO_ID_INPUT_SELECTOR: str = "#id"  # 로그인 페이지의 ID 입력 필드
    SMINFO_PW_INPUT_SELECTOR: str = "#pwd"  # 로그인 페이지의 PW 입력 필드
    SMINFO_LOGIN_BUTTON_SELECTOR: str = "#contents_sub > div:nth-child(3) > div > div.login_lr_box.clearfix > div.lr_text_r > div:nth-child(1) > form > button"  # 로그인 페이지의 실제 로그인 실행 버튼 선택자로 복원
    # SMINFO_LOGIN_BUTTON_SELECTOR: str = "button.login_btn_comm" # 이전 PRD 기반 일반 선택자

    # 로그인 성공 후 나타나는 '로그아웃' 버튼 (실제로는 버튼 내부 span의 텍스트로 판단)
    # LOGOUT_BUTTON_SELECTOR: str = "#wrap > div.header.clearfix > div.global_box > ul > li:nth-child(2) > a[onclick*='fnLogout']" # 기존 헤더 로그아웃 버튼
    LOGOUT_BUTTON_SELECTOR: str = "#main_link > div > div.main_login_box.m_main_login_box > div > form > fieldset > div > button > span" # 메인 영역 로그인 버튼 내부 span
    LOGGED_IN_TEXT_INDICATOR: str = "로그아웃" # 로그인 성공 시 LOGOUT_BUTTON_SELECTOR 내부 span에 표시될 텍스트
    LOGIN_BOX_LOGIN_BUTTON_SELECTOR: str = "#main_link > div > div.main_login_box.m_main_login_box > div > form > fieldset > div > button" # 로그인 상태에 따라 내부 span 텍스트가 바뀌는 실제 버튼 요소


    # 로그인 실패 시 특정 메시지 (예: "아이디 또는 비밀번호가 일치하지 않습니다.") - 실제 메시지 확인 필요
    # LOGIN_ERROR_MESSAGE_SELECTOR: str = "p.error_message_class"
    # LOGIN_ERROR_EXPECTED_TEXT: str = "아이디 또는 비밀번호가" # 오류 메시지의 일부

    # --- GNB 메뉴 선택자 (로그인 검증 및 스크레이퍼에서 사용) ---
    GNB_MENU_FIRST_LEVEL_SELECTOR: str = "#wrap > div.gnb > div > ul > li:nth-child(1) > a" # 예: "중소기업현황"
    GNB_MENU_SECOND_LEVEL_SELECTOR: str = "#wrap > div.gnb > div > ul > li:nth-child(1) > ul > li:nth-child(1) > a" # 예: "기업정보"

    # --- 네비게이션 및 검색 페이지 선택자 ---

    @classmethod
    def get_html_snapshot_path(cls, business_registration_number: str) -> str:
        """지정된 사업자등록번호에 대한 HTML 스냅샷 저장 경로를 반환합니다."""
        # HTML_SNAPSHOT_BASE_PATH 아래에 사업자등록번호로 된 폴더를 생성
        return os.path.join(cls.HTML_SNAPSHOT_BASE_PATH, business_registration_number)

# 설정 객체 인스턴스화 (애플리케이션 전역에서 사용 가능하도록)
# 사용 예시: from src.crawler.config import settings
# print(settings.SMINFO_ID)
settings = Config()

if __name__ == '__main__':
    # 테스트용: 설정값이 잘 로드되는지 확인
    print(f"SMINFO ID: {settings.SMINFO_ID}")
    print(f"SMINFO PW: {settings.SMINFO_PW}")
    print(f"SMINFO Base URL: {settings.SMINFO_BASE_URL}")
    print(f"SMINFO Login URL: {settings.SMINFO_LOGIN_URL}")
    print(f"API Host: {settings.API_HOST}")
    print(f"API Port: {settings.API_PORT}")
    print(f"Save HTML Snapshots: {settings.SAVE_HTML_SNAPSHOTS} (Type: {type(settings.SAVE_HTML_SNAPSHOTS)})")
    print(f"HTML Snapshot Base Path: {settings.HTML_SNAPSHOT_BASE_PATH}")
    
    # .env 파일에 SMINFO_ID=test_user 를 설정하고 실행해보세요.
    # 만약 .env 파일이 없다면 기본값이 출력됩니다.
    # SAVE_HTML_SNAPSHOTS="False" 로 설정하고 테스트해보세요.

    # HTML 스냅샷 경로 생성 예시
    brn = "123-45-67890"
    snapshot_dir = settings.get_html_snapshot_path(brn)
    print(f"Snapshot directory for {brn}: {snapshot_dir}")
    # 실제 디렉토리 생성은 Scraper 등에서 수행 