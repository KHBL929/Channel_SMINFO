import asyncio
import os
from playwright.async_api import Page, Dialog
from bs4 import BeautifulSoup
import datetime

from src.crawler.config import settings
from src.crawler.login import LoginManager # LoginManager 임포트

# --- 예시 선택자 (실제 값은 Selector.md 또는 config.py 에서 관리) ---
# 검색 페이지 URL (또는 메인 페이지에서 검색으로 진입하는 경로)
# SEARCH_PAGE_URL = f"{settings.SMINFO_BASE_URL}/search/company" # 예시 URL, 실제 주소 확인 필요
SEARCH_PAGE_URL = settings.SEARCH_PAGE_URL # config.py에서 가져오도록 수정

# 검색어 입력 필드
SEARCH_TEXT_INPUT_SELECTOR = settings.SEARCH_TEXT_INPUT_SELECTOR
# 검색 버튼
SEARCH_BUTTON_SELECTOR = settings.SEARCH_BUTTON_SELECTOR
# 검색 유형 선택 (회사명/사업자번호) - 필요시 추가
# SEARCH_TYPE_SELECT_SELECTOR = "#search_type_select"

# 검색 결과 테이블 (기업 목록)
RESULTS_TABLE_SELECTOR = settings.RESULTS_TABLE_SELECTOR
# 검색 결과 내 기업명, 대표자명 등의 선택자 예시 (테이블 구조에 따라 상세화)
# COMPANY_NAME_IN_TABLE_SELECTOR = "tr:first-child td:nth-child(2)" # Selector.md 반영
# CEO_NAME_IN_TABLE_SELECTOR = "tr:first-child td:nth-child(3)"         # Selector.md 반영
# BUSINESS_REG_NO_IN_TABLE_SELECTOR = "tr:first-child td:nth-child(4)"      # Selector.md 반영
# ADDRESS_IN_TABLE_SELECTOR = "tr:first-child td:nth-child(5)"          # Selector.md 반영 (주소 추가)

# 재무 정보 섹션/테이블 선택자 (상세 페이지 또는 검색 결과 내)
FINANCIAL_TABLE_SELECTOR_BASE = settings.FINANCIAL_TABLE_SELECTOR_BASE
FINANCIAL_TABLE_CAPTION_TEXT = settings.FINANCIAL_TABLE_CAPTION_TEXT
# 검색된 회사명 표시 제목 (매출/이익 정보 추출 시)
COMPANY_TITLE_SELECTOR = settings.COMPANY_TITLE_SELECTOR

# 상세 페이지 내 대표자명 선택자 (추가)
CEO_NAME_IN_DETAIL_PAGE_SELECTOR = settings.CEO_NAME_IN_DETAIL_PAGE_SELECTOR

# 재무 테이블 내 연도별 데이터 행 선택자 (추가)
YEAR_ROW_SELECTOR = settings.YEAR_ROW_SELECTOR

# "매출현황 정보가 없습니다." 메시지 선택자
# NO_FINANCIAL_DATA_MESSAGE_SELECTOR = "div.no_data_message_class" # 예시
# Selector.md에 명시적인 '정보 없음' 메시지 선택자는 없으나, 필요시 추가 가능. 일단 유지.
# NO_FINANCIAL_DATA_MESSAGE_SELECTOR = "div.no_data_message_class" # 기존 예시 유지 (Selector.md에 없음)

# 페이지네이션 "다음 페이지" 버튼
# NEXT_PAGE_BUTTON_SELECTOR = "a.next_page_button_class" # 예시
# Selector.md에 명시적인 페이지네이션 선택자는 없으나, PRD에는 기능 요구사항이 있음. 일단 유지.
# NEXT_PAGE_BUTTON_SELECTOR = "a.next_page_button_class" # 기졸 예시 유지 (Selector.md에 없음)
# 페이지네이션 현재 페이지/전체 페이지 정보 (있다면)
# CURRENT_PAGE_SELECTOR = "span.current_page_class"
# TOTAL_PAGE_SELECTOR = "span.total_page_class"

class ScrapingError(Exception):
    """크롤링 과정에서 발생하는 특정 에러"""
    pass

class CompanyData:
    """추출된 기업 정보를 담는 데이터 클래스 (Pydantic 모델로 대체 가능)"""
    def __init__(self, name: str | None = None, ceo: str | None = None, brn: str | None = None, financials: dict | None = None, status: str = "정상"):
        self.name = name
        self.ceo = ceo
        self.business_registration_number = brn
        self.financials = financials if financials else {}
        self.html_snapshot_path: str | None = None
        self.status = status # 기업 상태 (예: "정상", "정보없음", "페이지로드실패")

    def __str__(self):
        return f"Company(name={self.name}, brn={self.business_registration_number}, status={self.status}, financials={self.financials})"

class Scraper:
    """
    SMINFO 웹사이트에서 기업 정보를 검색하고 추출합니다.
    로그인된 Page 객체와 LoginManager 객체를 사용하여 작업을 수행합니다.
    """
    def __init__(self, page: Page, login_manager: LoginManager):
        self.page = page
        self.login_manager = login_manager
        self.detected_private_company_popup = False # 정보 비공개 팝업 감지 플래그

    async def _save_html_snapshot(self, content: str, business_reg_number: str, snapshot_name_prefix: str = "financial") -> str | None:
        """주어진 HTML 내용을 스냅샷으로 저장합니다 (설정이 True인 경우)."""
        if not settings.SAVE_HTML_SNAPSHOTS:
            return None
        
        try:
            sanitized_brn = business_reg_number.replace("-", "")
            snapshot_dir = settings.get_html_snapshot_path(sanitized_brn)
            os.makedirs(snapshot_dir, exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"{timestamp}_{snapshot_name_prefix}_page.html"
            filepath = os.path.join(snapshot_dir, filename)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"HTML 스냅샷 저장 완료: {filepath}")
            return filepath
        except Exception as e:
            print(f"HTML 스냅샷 저장 중 오류 발생: {e}")
            return None

    async def _handle_dialog(self, dialog: Dialog):
        """팝업(다이얼로그) 자동 닫기 핸들러"""
        print(f"팝업 발견: Type={dialog.type}, Message='{dialog.message}'. 자동으로 닫습니다.")
        if "정보비공개" in dialog.message:
            print("정보 비공개 관련 팝업 메시지 감지됨.")
            self.detected_private_company_popup = True
        await dialog.dismiss()

    async def search_company(self, search_query: str, search_type: str = "business_registration_number") -> bool:
        print(f"'{search_query}' ({search_type}) 검색 시작 (메인 페이지 메뉴 클릭 방식)...")
        headless_mode_prefix = "hl_true_"
        
        self.page.on("dialog", self._handle_dialog)
        print("팝업 자동 닫기 핸들러 등록됨.")

        try:
            # STEP 1: 현재 페이지가 메인 페이지인지 확인하고, 아니면 메인 페이지로 이동
            current_url_normalized = self.page.url.split('?')[0]
            expected_main_page_url = settings.SMINFO_MAIN_PAGE_URL.split('?')[0]

            if current_url_normalized != expected_main_page_url:
                print(f"현재 SMINFO 메인 페이지({expected_main_page_url})가 아닙니다. (현재: {self.page.url}). 메인 페이지로 이동합니다.")
                # LoginManager.login()이 이미 호출되어 로그인 상태라고 가정하고, 메인 페이지로 직접 이동 시도
                # 만약 로그인 풀렸을 경우를 대비하려면 login_manager.login() 재호출 고려
                if not self.login_manager.is_logged_in: # 간단한 플래그 확인
                    print("경고: LoginManager 상태가 로그아웃으로 되어있습니다. 재로그인을 시도합니다.")
                    await self.login_manager.login()
                    if not self.login_manager.is_logged_in:
                         raise ScrapingError("메인 페이지 이동 전 재로그인 시도 실패.")
                else:
                    await self.page.goto(settings.SMINFO_MAIN_PAGE_URL, wait_until="networkidle", timeout=30000)
                
                # 메인 페이지 이동 후 URL 재확인
                if self.page.url.split('?')[0] != expected_main_page_url:
                    await self._save_html_snapshot(await self.page.content(), search_query, f"{headless_mode_prefix}nav_to_main_failed_before_menu")
                    raise ScrapingError(f"메인 페이지({expected_main_page_url})로 이동 실패. 현재 URL: {self.page.url}")
                print(f"메인 페이지로 성공적으로 이동/확인됨: {self.page.url}")
            else:
                print(f"이미 SMINFO 메인 페이지({self.page.url})에 있습니다.")
            
            await self._save_html_snapshot(await self.page.content(), search_query, f"{headless_mode_prefix}on_main_page_before_menu_click")

            # STEP 2: 메인 페이지에서 "중소기업현황 > 기업정보" 메뉴 클릭
            # 1차 메뉴 "중소기업현황"을 클릭하면 하위 "기업정보"가 나타나는 방식
            gnb_main_menu_click_target_selector = "#wrap > div.gnb > div > ul > li:nth-child(1) > a" # "중소기업현황" 링크로 가정
            gnb_submenu_enterprise_info_selector = "#wrap > div.gnb > div > ul > li:nth-child(1) > ul > li:nth-child(1) > a" # "기업정보" 링크

            print(f"메인 페이지에서 GNB 1차 메뉴 클릭 시도: {gnb_main_menu_click_target_selector}")
            main_menu_locator = self.page.locator(gnb_main_menu_click_target_selector)
            try:
                await main_menu_locator.wait_for(state="visible", timeout=10000)
                await main_menu_locator.click(timeout=5000)
                print(f"GNB 1차 메뉴({gnb_main_menu_click_target_selector}) 클릭 완료.")
                await asyncio.sleep(0.8) # 하위 메뉴가 나타나고 안정화될 시간 확보 (0.5 -> 0.8)
            except Exception as e_menu_click:
                await self._save_html_snapshot(await self.page.content(), search_query, f"{headless_mode_prefix}gnb_main_menu_click_failed")
                raise ScrapingError(f"GNB 1차 메뉴({gnb_main_menu_click_target_selector}) 클릭 중 오류: {e_menu_click}")

            await self._save_html_snapshot(await self.page.content(), search_query, f"{headless_mode_prefix}after_main_menu_click_before_submenu_wait")

            # --- 2차 메뉴 클릭 전 로그인 상태 재확인 및 재로그인 --- START
            print("2차 메뉴 클릭 전 로그인 상태 재확인...")
            if not await self.login_manager.check_login_status():
                print("로그아웃 상태로 확인됨 (2차 메뉴 클릭 전). 재로그인 시도...")
                try:
                    # 재로그인 시, login() 메서드는 이미 메인 페이지로 이동하는 로직을 포함할 수 있음.
                    # login() 후 현재 페이지가 어디인지, 그리고 GNB 메뉴를 다시 클릭해야 하는지 고려 필요.
                    # 여기서는 login()이 성공하면 현재 페이지에서 계속 진행한다고 가정.
                    await self.login_manager.login()
                    if not self.login_manager.is_logged_in:
                        raise ScrapingError("2차 메뉴 클릭 전 재로그인 시도 실패.")
                    print("재로그인 성공 (2차 메뉴 클릭 전).")
                    # 재로그인 후에는 페이지가 메인 페이지일 가능성이 높음.
                    # 따라서, GNB 1차 메뉴를 다시 클릭해야 할 수 있음.
                    # 현재 로직은 바로 2차 메뉴로 진행하므로, 문제가 되면 이 부분을 수정해야 함.
                    print("주의: 재로그인 후 GNB 1차 메뉴를 다시 클릭해야 할 수 있습니다. 현재는 바로 2차 메뉴로 진행합니다.")
                    await asyncio.sleep(1.5) # 재로그인 및 페이지 안정화 시간 추가
                except Exception as e_relogin_before_submenu:
                    await self._save_html_snapshot(await self.page.content(), search_query, f"{headless_mode_prefix}relogin_failed_before_submenu")
                    raise ScrapingError(f"2차 메뉴 클릭 전 재로그인 시도 중 오류: {e_relogin_before_submenu}")
            else:
                print("로그인 상태 유지 확인됨 (2차 메뉴 클릭 전).")
            # --- 2차 메뉴 클릭 전 로그인 상태 재확인 및 재로그인 --- END

            print(f"GNB 2차 메뉴 ('기업정보') 클릭 시도: {gnb_submenu_enterprise_info_selector}")
            submenu_item_locator = self.page.locator(gnb_submenu_enterprise_info_selector)
            try:
                # 1차 메뉴 클릭 후 2차 메뉴가 보이기를 기다림
                await submenu_item_locator.wait_for(state="visible", timeout=10000) 
                print(f"GNB 2차 메뉴({gnb_submenu_enterprise_info_selector}) 확인됨 (visible).")
            except Exception as e_submenu_visible:
                await self._save_html_snapshot(await self.page.content(), search_query, f"{headless_mode_prefix}gnb_submenu_item_not_visible_after_click")
                raise ScrapingError(f"GNB 2차 메뉴({gnb_submenu_enterprise_info_selector})를 찾거나 기다리는 중 오류 (1차 메뉴 클릭 후): {e_submenu_visible}")

            print("GNB 2차 메뉴('기업정보') 클릭 및 네비게이션 대기...")
            # "기업정보" 메뉴 클릭 시 페이지 이동이 없을 수 있으므로 expect_navigation 제거하고, 다음 요소 대기로 변경
            await submenu_item_locator.click(timeout=5000)
            print(f"GNB 2차 메뉴('기업정보') 클릭 완료. 클릭 후 즉시 URL: {self.page.url}")
            await self._save_html_snapshot(await self.page.content(), search_query, f"{headless_mode_prefix}after_submenu_click_content")
            
            # 페이지 이동(navigation)을 기다리는 대신, 검색 입력 필드가 나타나는 것을 기다림
            try:
                print(f"검색 입력 필드({settings.SEARCH_TEXT_INPUT_SELECTOR}) 대기 시작. 현재 URL: {self.page.url}")
                await self.page.wait_for_selector(settings.SEARCH_TEXT_INPUT_SELECTOR, timeout=15000, state="visible")
                print(f"GNB 메뉴 클릭 후 검색 페이지({settings.SEARCH_TEXT_INPUT_SELECTOR} 확인)로 이동/로드 완료.")
            except Exception as e_search_input_after_menu:
                await self._save_html_snapshot(await self.page.content(), search_query, f"{headless_mode_prefix}search_input_not_found_after_menu_click_no_nav")
                # 현재 URL이 검색 페이지 URL과 같은지 비교하여 추가 정보 제공
                if self.page.url.split('?')[0] != settings.SEARCH_PAGE_URL.split('?')[0]:
                     print(f"경고: 검색 입력 필드를 찾지 못했고, 현재 URL({self.page.url})이 예상 검색 페이지 URL({settings.SEARCH_PAGE_URL})과 다릅니다.")
                raise ScrapingError(f"GNB 메뉴 클릭 후 검색 입력 필드({settings.SEARCH_TEXT_INPUT_SELECTOR}) 대기 중 오류: {e_search_input_after_menu}")
            await self._save_html_snapshot(await self.page.content(), search_query, f"{headless_mode_prefix}after_gnb_menu_click_input_visible")
            search_input = self.page.locator(settings.SEARCH_TEXT_INPUT_SELECTOR)
            await search_input.fill(search_query)
            print(f"검색어 입력: {search_query}")
            await self._save_html_snapshot(await self.page.content(), search_query, f"{headless_mode_prefix}after_input_fill_after_menu")
            await asyncio.sleep(settings.DEFAULT_SLEEP_TIME_SHORT)
            search_button = self.page.locator(settings.SEARCH_BUTTON_SELECTOR)
            try:
                await self._save_html_snapshot(await self.page.content(), search_query, f"{headless_mode_prefix}before_search_button_wait_after_menu")
                await search_button.wait_for(state="visible", timeout=15000)
            except Exception as e_button_wait:
                await self._save_html_snapshot(await self.page.content(), search_query, f"{headless_mode_prefix}search_button_not_ready_after_menu")
                raise ScrapingError(f"메뉴 클릭 후 검색 버튼({settings.SEARCH_BUTTON_SELECTOR}) 대기 중 오류: {e_button_wait}")
            print("검색 버튼 클릭 시도 (메뉴 클릭 후)...")
            # 검색 버튼 클릭 시에는 네비게이션 발생 가정
            async with self.page.expect_navigation(wait_until="domcontentloaded", timeout=30000):
                await search_button.click()
            print("검색 버튼 클릭 완료 (메뉴 클릭 후), 네비게이션 또는 페이지 변경 대기 완료.")
            await asyncio.sleep(1.0)
            await self._save_html_snapshot(await self.page.content(), search_query, f"{headless_mode_prefix}after_search_click_after_menu")
            try:
                await self._save_html_snapshot(await self.page.content(), search_query, f"{headless_mode_prefix}before_results_table_wait_after_menu")
                await self.page.wait_for_selector(settings.RESULTS_TABLE_SELECTOR, timeout=15000, state="visible")
                print(f"검색 결과 테이블({settings.RESULTS_TABLE_SELECTOR}) 확인됨 (메뉴 클릭 후).")
                await self._save_html_snapshot(await self.page.content(), search_query, f"{headless_mode_prefix}after_results_table_found_after_menu")
            except Exception:
                await self._save_html_snapshot(await self.page.content(), search_query, f"{headless_mode_prefix}results_table_not_found_trying_title_after_menu")
                try:
                    await self.page.wait_for_selector(settings.COMPANY_TITLE_SELECTOR, timeout=10000, state="visible")
                    print(f"검색 결과 상세 페이지 제목({settings.COMPANY_TITLE_SELECTOR}) 확인됨 (결과 테이블 없이 바로 이동, 메뉴 클릭 후).")
                    await self._save_html_snapshot(await self.page.content(), search_query, f"{headless_mode_prefix}after_detail_title_found_after_menu")
                except Exception as e_detail_title:
                    print(f"경고: 검색 결과 테이블 또는 상세 페이지 제목을 확인할 수 없습니다 (메뉴 클릭 후). 페이지 URL: {self.page.url}. 오류: {e_detail_title}")
                    await self._save_html_snapshot(await self.page.content(), search_query, f"{headless_mode_prefix}search_result_ambiguous_final_after_menu")
            print(f"검색 실행 후 현재 URL (메뉴 클릭 후): {self.page.url}")
            return True
        
        except Exception as e:
            error_message = f"기업 검색 중 예외 발생 (메뉴 클릭 방식, {search_query}): {e}"
            print(error_message)
            import traceback
            print(traceback.format_exc())
            try:
                if self.page and not self.page.is_closed():
                    await self._save_html_snapshot(await self.page.content(), search_query, f"{headless_mode_prefix}search_company_exception_final_menu_flow")
            except Exception as snapshot_e:
                print(f"search_company 예외 상황 스냅샷 저장 중 추가 오류: {snapshot_e}")
            raise ScrapingError(error_message) from e
        finally:
            if hasattr(self.page, '_events') and 'dialog' in self.page._events and self._handle_dialog in self.page._events['dialog']:
                try: # Listener가 이미 제거되었을 수 있는 경우를 대비
                    self.page.remove_listener("dialog", self._handle_dialog)
                    print("팝업 자동 닫기 핸들러 제거됨.")
                except Exception as e_remove_listener:
                    print(f"팝업 핸들러 제거 중 오류 (무시 가능): {e_remove_listener}")
    
    async def extract_company_basic_info_from_list(self) -> list[CompanyData]:
        """
        현재 페이지의 검색 결과 목록에서 여러 기업의 기본 정보를 추출합니다.
        (사업자등록번호 검색만 지원하므로 현재 사용되지 않음)
        """
        print("검색 결과 목록에서 기본 정보 추출 시작... (현재 미사용)")
        companies: list[CompanyData] = []
        # ... (이하 로직 전체 주석 처리) ...
        return companies

    async def extract_financial_info_for_company(self, company_data: CompanyData, target_years: list[str]) -> CompanyData:
        """
        주어진 CompanyData 객체에 해당하는 기업의 재무 정보를 추출하여 업데이트합니다.
        이 메서드는 특정 기업의 상세 페이지에서 호출됩니다.

        Args:
            company_data (CompanyData): 재무 정보를 채울 CompanyData 객체.
            target_years (list[str]): 추출 대상 연도 목록 (예: ["2024", "2023", "2022"]).

        Returns:
            CompanyData: 재무 정보가 업데이트된 CompanyData 객체.
        """
        if not company_data.business_registration_number:
            print("사업자등록번호가 없어 재무 정보를 조회할 수 없습니다.")
            company_data.status = "오류 (BRN 없음)"
            return company_data
        
        print(f"'{company_data.name}({company_data.business_registration_number})' 재무 정보 추출 시작 (대상 연도: {target_years})...")
        
        extracted_financials = {}

        try:
            # 대표자명 추출
            if not company_data.ceo:
                try:
                    ceo_element = self.page.locator(settings.CEO_NAME_IN_DETAIL_PAGE_SELECTOR)
                    if await ceo_element.is_visible(timeout=3000): # 상세 페이지 요소이므로 타임아웃 약간 줄임
                        company_data.ceo = (await ceo_element.text_content() or "").strip()
                        print(f"상세 페이지에서 대표자명 추출: {company_data.ceo}")
                    else:
                         print(f"상세 페이지에서 대표자명 요소({settings.CEO_NAME_IN_DETAIL_PAGE_SELECTOR})를 찾을 수 없거나 보이지 않습니다.")
                except Exception as ceo_e:
                    print(f"상세 페이지에서 대표자명 추출 중 오류: {ceo_e}")
            
            print(f"현재 페이지 URL: {self.page.url} (재무정보 추출 전)")

            page_content_html = await self.page.content()
            soup = BeautifulSoup(page_content_html, "html.parser")

            snapshot_path = await self._save_html_snapshot(page_content_html, company_data.business_registration_number, "financial_detail")
            if snapshot_path:
                company_data.html_snapshot_path = snapshot_path

            financial_table = None
            candidate_tables = soup.select(settings.FINANCIAL_TABLE_SELECTOR_BASE)
            print(f"{len(candidate_tables)}개의 후보 재무 테이블 ({settings.FINANCIAL_TABLE_SELECTOR_BASE}) 발견.")
            for table in candidate_tables:
                caption_tag = table.find("caption")
                if caption_tag and settings.FINANCIAL_TABLE_CAPTION_TEXT in caption_tag.get_text(strip=True):
                    financial_table = table
                    print(f"'{settings.FINANCIAL_TABLE_CAPTION_TEXT}' 캡션을 가진 재무 테이블 찾음.")
                    break
            
            if not financial_table:
                print(f"'{settings.FINANCIAL_TABLE_CAPTION_TEXT}' 캡션을 가진 재무 테이블 ({settings.FINANCIAL_TABLE_SELECTOR_BASE})을 찾을 수 없습니다.")
                page_company_title_element = soup.select_one(settings.COMPANY_TITLE_SELECTOR)
                if page_company_title_element:
                    page_company_title = page_company_title_element.get_text(strip=True)
                    print(f"현재 페이지의 회사명 표시 제목: {page_company_title}")
                    if not company_data.name and page_company_title:
                        company_data.name = page_company_title
                        print(f"회사명을 페이지 제목에서 가져옴: {company_data.name}")
                    elif company_data.name and company_data.name not in page_company_title:
                        print(f"경고: 스크랩 대상 회사명({company_data.name})과 페이지에 표시된 회사명({page_company_title})이 다를 수 있습니다.")
                else:
                    print(f"페이지 내 회사명 표시 제목({settings.COMPANY_TITLE_SELECTOR})을 찾을 수 없습니다.")
                
                company_data.financials = {}
                # 재무 테이블이 없으면 상태 업데이트
                if company_data.status == "정상": # 다른 오류가 아니었다면
                    company_data.status = "정보없음 (재무테이블 부재)"
                    print(f"'{company_data.name}': 재무 테이블을 찾을 수 없어 상태를 '{company_data.status}'로 설정.")
                return company_data

            rows = financial_table.select(settings.YEAR_ROW_SELECTOR) 
            print(f"재무 테이블 내 {len(rows)}개의 데이터 행 발견.")

            def sanitize_figure(text_value: str) -> float | None:
                if not text_value or not isinstance(text_value, str):
                    return None
                cleaned_text = text_value.strip().replace(",", "")
                if cleaned_text == "-" or cleaned_text == "": 
                    return None
                try:
                    value = float(cleaned_text)
                    return value * 1000 # 천원 단위 적용
                except ValueError:
                    print(f"경고: 숫자 변환 실패 '{text_value}' -> '{cleaned_text}'")
                    return None

            found_data_for_any_target_year = False
            for row in rows:
                cells = row.find_all("td") 
                COL_IDX_YEAR = 0
                COL_IDX_REVENUE = 4 
                COL_IDX_OPERATING_PROFIT = 5
                MIN_CELLS_PER_ROW = max(COL_IDX_YEAR, COL_IDX_REVENUE, COL_IDX_OPERATING_PROFIT) + 1

                if len(cells) < MIN_CELLS_PER_ROW:
                    print(f"행에 충분한 셀이 없습니다 ({len(cells)}/{MIN_CELLS_PER_ROW}). 건너<0xEB><0x9B><0x84>.")
                    continue

                year_text = cells[COL_IDX_YEAR].get_text(strip=True)
                current_row_year = year_text.split("-")[0].strip() if "-" in year_text else year_text.strip()
                
                if not current_row_year.isdigit() or len(current_row_year) != 4:
                    print(f"유효하지 않은 연도 형식: '{year_text}' -> '{current_row_year}'. 건너<0xEB><0x9B><0x84>.")
                    continue

                # 수정 시작: target_years가 None이거나 비어있으면 모든 연도를 처리, 아니면 필터링
                process_this_year = True  # 기본적으로 모든 연도 처리
                if target_years:  # target_years가 None이 아니거나 비어있지 않은 경우에만 필터링
                    if current_row_year not in target_years:
                        process_this_year = False
                
                if process_this_year:
                    found_data_for_any_target_year = True # target_years 필터링과 무관하게 데이터 찾았는지 여부
                    revenue_text = cells[COL_IDX_REVENUE].get_text(strip=True)
                    operating_profit_text = cells[COL_IDX_OPERATING_PROFIT].get_text(strip=True)
                    revenue = sanitize_figure(revenue_text)
                    operating_profit = sanitize_figure(operating_profit_text)
                    if revenue is not None: 
                        extracted_financials[f"{current_row_year}_revenue"] = revenue
                    if operating_profit is not None:
                        extracted_financials[f"{current_row_year}_operating_profit"] = operating_profit
                    print(f"  {current_row_year}년 데이터 추출: 매출액='{revenue_text}'({revenue}), 영업이익='{operating_profit_text}'({operating_profit})")
            
            if not found_data_for_any_target_year and len(rows) > 0:
                print(f"주의: 재무 테이블은 찾았으나, 대상 연도({target_years})에 대한 데이터를 찾지 못했습니다.")
            elif len(rows) == 0 and financial_table: 
                 print(f"주의: 재무 테이블({settings.FINANCIAL_TABLE_SELECTOR_BASE})은 찾았으나 내부에 데이터 행이 없습니다.")

            company_data.financials = extracted_financials

            if company_data.status == "정상": # 다른 오류가 아닌 경우에만 상태 업데이트
                if not company_data.ceo and not company_data.financials:
                    company_data.status = "정보없음 (대표자명 및 재무)"
                    print(f"'{company_data.name}': 대표자명 및 재무정보가 없어 상태를 '{company_data.status}'로 설정.")
                elif not company_data.financials:
                    company_data.status = "정보없음 (재무)"
                    print(f"'{company_data.name}': 재무정보가 없어 상태를 '{company_data.status}'로 설정.")
            
            print(f"'{company_data.name}' 재무 정보 추출 완료 (상태: {company_data.status}): {company_data.financials}")
            return company_data
        except Exception as e:
            error_message = f"'{company_data.name}' 재무 정보 추출 중 오류: {e}"
            import traceback
            print(f"{error_message}\\n{traceback.format_exc()}") 
            company_data.financials = extracted_financials
            if company_data.status == "정상": # 다른 오류가 아니었다면
                company_data.status = "오류 (정보추출중)"
            return company_data

    async def navigate_to_next_page(self) -> bool:
        """
        페이지네이션을 사용하여 다음 검색 결과 페이지로 이동합니다.
        (사업자등록번호 검색만 지원하므로 현재 사용되지 않음)
        """
        print("다음 페이지로 이동 시도... (현재 미사용)")
        # ... (이하 로직 전체 주석 처리) ...
        return False

    async def scrape_companies_with_financials(self, search_query: str, search_type: str = "business_registration_number", target_years: list[str] | None = None, max_pages: int = 1) -> list[CompanyData]:
        # 각 회사 검색 시도 전에 비공개 팝업 플래그 리셋
        self.detected_private_company_popup = False
        
        all_companies_data: list[CompanyData] = []

        if search_type != "business_registration_number":
            print(f"경고: 현재 search_type='{search_type}'은(는) 지원하지 않습니다. 사업자등록번호 검색으로 진행합니다.")

        try:
            # search_company가 성공하면 True를 반환하고, 실패하면 ScrapingError 발생
            await self.search_company(search_query, "business_registration_number")
            # search_company 성공 시, 페이지는 검색 결과 목록 또는 상세 페이지에 있어야 함
            
            print(f"검색 성공 후 페이지 URL: {self.page.url}")

            # 사업자등록번호 검색은 보통 단일 결과를 상세 페이지로 바로 보여주거나,
            # 결과 목록에 하나만 표시하고 해당 링크를 클릭해야 상세 정보로 이동.
            # 여기서는 결과 목록에서 링크를 찾아 클릭하는 로직을 가정.
            # 만약 search_company에서 이미 상세페이지로 이동했다면, 이 부분은 건너뛸 수 있도록 조건 추가 필요.

            # 현재 URL이 이미 상세 페이지인지 (예: COMPANY_TITLE_SELECTOR가 있는지) 확인 가능
            # 여기서는 결과 목록의 링크를 클릭하는 것을 기본으로 함
            
            brn_normalized = search_query.replace("-", "")
            company_name_from_link_text = f"미확인({brn_normalized})"
            
            # 상세 페이지 링크가 존재하는지 확인 (RESULTS_TABLE_SELECTOR 내부에 있을 수 있음)
            # 또는 search_company의 결과로 이미 상세페이지에 도달했을 수 있음
            # 우선 상세페이지 제목이 있는지 먼저 확인
            is_on_detail_page = False
            try:
                await self.page.wait_for_selector(settings.COMPANY_TITLE_SELECTOR, timeout=1000, state="visible")
                is_on_detail_page = True
                print(f"이미 상세 페이지에 있는 것으로 판단됨 (타이틀: {settings.COMPANY_TITLE_SELECTOR} 확인)")
            except Exception:
                 print(f"상세 페이지 제목({settings.COMPANY_TITLE_SELECTOR})을 바로 찾지 못함. 결과 목록에서 링크 클릭 시도.")

            if not is_on_detail_page:
                print(f"사업자등록번호 검색 결과를 클릭하여 상세 페이지로 이동 시도 (선택자: {settings.SEARCH_RESULT_DETAIL_LINK_SELECTOR})")
                try:
                    detail_page_link = self.page.locator(settings.SEARCH_RESULT_DETAIL_LINK_SELECTOR)
                    if not await detail_page_link.is_visible(timeout=15000):
                        await self._save_html_snapshot(await self.page.content(), brn_normalized, "search_result_link_not_found_final")
                        # 비공개 팝업이 이전에 감지되었다면 상태 변경
                        status_to_set = "정보없음 (검색결과 링크 없음)"
                        if self.detected_private_company_popup:
                            status_to_set = "비공개 (링크없음)" # 또는 "정보없음 (비공개 요청)"
                            print("비공개 팝업 감지 후 결과 링크 없음 처리.")
                        company_data_item = CompanyData(name=company_name_from_link_text, brn=brn_normalized, status=status_to_set)
                        all_companies_data.append(company_data_item)
                        return all_companies_data
                    company_name_from_link_text = (await detail_page_link.text_content() or brn_normalized).strip()
                    print(f"클릭할 검색 결과 링크의 텍스트(예상 회사명): {company_name_from_link_text}")

                    # 링크 클릭 시도 전, 비공개 팝업 플래그를 다시 한번 확인 (클릭 전 팝업 가능성)
                    if self.detected_private_company_popup:
                        print("결과 목록의 링크 클릭 전 이미 비공개 팝업이 감지되었습니다. '비공개'로 처리합니다.")
                        company_data_item = CompanyData(name=company_name_from_link_text, brn=brn_normalized, status="비공개")
                        all_companies_data.append(company_data_item)
                        return all_companies_data

                    # 상세 페이지 링크 클릭
                    await detail_page_link.click(timeout=10000) # 클릭 자체의 타임아웃
                    # 클릭 후 네비게이션을 기다리는 대신, 상세 페이지의 특정 요소가 나타나는지 확인
                    try:
                        await self.page.wait_for_selector(settings.COMPANY_TITLE_SELECTOR, timeout=20000, state="visible")
                        print(f"상세 페이지로 정상 이동/로드 완료 (타이틀 확인). 현재 URL: {self.page.url}")
                    except Exception as e_detail_load_after_click:
                        # 네비게이션 실패 또는 상세 페이지 로드 실패
                        await self._save_html_snapshot(await self.page.content(), brn_normalized, "detail_page_load_failed_after_link_click")
                        status_after_click_fail = "오류 (상세페이지 로드 실패)"
                        if self.detected_private_company_popup: # 클릭 도중 또는 직후 팝업 감지
                             status_after_click_fail = "비공개 (상세페이지 로드 중 감지)"
                             print("상세 페이지 로드 실패, 비공개 팝업 감지됨.")
                        company_data_item = CompanyData(name=company_name_from_link_text, brn=brn_normalized, status=status_after_click_fail)
                        all_companies_data.append(company_data_item)
                        print(f"상세 페이지 링크 클릭 후 상세 페이지 로드 실패: {e_detail_load_after_click}")
                        return all_companies_data
                except Exception as e_link_click: 
                    await self._save_html_snapshot(await self.page.content(), brn_normalized, "search_result_link_click_generic_failed")
                    status_on_link_click_fail = f"오류 (결과링크클릭 중 예외)"
                    if self.detected_private_company_popup:
                        status_on_link_click_fail = "비공개 (결과링크 클릭 중 감지)"
                        print("결과 링크 클릭 중 예외 발생, 비공개 팝업 감지됨.")
                    company_data_item = CompanyData(name=company_name_from_link_text, brn=brn_normalized, status=status_on_link_click_fail)
                    all_companies_data.append(company_data_item)
                    print(f"상세 페이지 링크({settings.SEARCH_RESULT_DETAIL_LINK_SELECTOR}) 클릭 중 일반 오류: {e_link_click}")
                    return all_companies_data
            print(f"상세 페이지 처리 시작. 현재 URL: {self.page.url}")
            page_company_title_element = self.page.locator(settings.COMPANY_TITLE_SELECTOR)
            actual_company_name_on_page = company_name_from_link_text
            try:
                if await page_company_title_element.is_visible(timeout=5000):
                    actual_company_name_on_page = (await page_company_title_element.text_content() or company_name_from_link_text).strip()
                print(f"상세 페이지에서 확인된 회사명: {actual_company_name_on_page}")
            except Exception:
                 print(f"상세 페이지에서 회사명 제목({settings.COMPANY_TITLE_SELECTOR})을 찾을 수 없어 링크 텍스트 또는 BRN을 사용합니다.")
            company_data_item = CompanyData(name=actual_company_name_on_page, brn=brn_normalized, status="정상") 
            # 비공개 팝업이 최종적으로 여기서 한번 더 확인될 수 있음 (extract_financial_info_for_company 호출 전)
            if self.detected_private_company_popup:
                print("재무 정보 추출 직전 비공개 팝업 최종 감지. '비공개'로 처리합니다.")
                company_data_item.status = "비공개"
                # 비공개인 경우 재무정보 추출 시도하지 않고 바로 반환
                all_companies_data.append(company_data_item)
                return all_companies_data 
            company_full_data = await self.extract_financial_info_for_company(company_data_item, target_years)
            all_companies_data.append(company_full_data)
            return all_companies_data

        except ScrapingError as e:
            print(f"ScrapingError 발생 (in scrape_companies_with_financials): {e}")
            # search_company에서 ScrapingError 발생 시 해당 오류 상태를 반영한 CompanyData 객체 생성 시도
            brn_normalized_fallback = search_query.replace("-", "")
            status_on_scraping_error = f"오류 ({e})"
            if self.detected_private_company_popup:
                status_on_scraping_error = "비공개 (스크래핑 오류 중 감지)"
            company_data_item = CompanyData(name=f"미확인({brn_normalized_fallback})", brn=brn_normalized_fallback, status=status_on_scraping_error)
            all_companies_data.append(company_data_item)
            return all_companies_data
        except Exception as e:
            print(f"scrape_companies_with_financials 중 예상치 못한 오류 발생: {e}")
            import traceback
            print(traceback.format_exc())
            brn_normalized_fallback = search_query.replace("-", "")
            status_on_exception = "오류 (내부오류)"
            if self.detected_private_company_popup:
                status_on_exception = "비공개 (내부 오류 중 감지)"
            company_data_item = CompanyData(name=f"미확인({brn_normalized_fallback})", brn=brn_normalized_fallback, status=status_on_exception)
            all_companies_data.append(company_data_item)
            return all_companies_data

async def example_scraper_usage():
    from src.crawler.browser import BrowserManager
    from src.crawler.login import LoginError

    if "default_id" in settings.SMINFO_ID or "default_pw" in settings.SMINFO_PW or not settings.SMINFO_ID or not settings.SMINFO_PW:
        print("오류: .env 파일에 실제 SMINFO_ID와 SMINFO_PW를 설정해야 예제를 실행할 수 있습니다.")
        print("config.py의 SMINFO_ID, SMINFO_PW가 유효한 값인지 확인하세요.")
        return

    async with BrowserManager(headless=False) as bm: 
        page = await bm.new_page()
        login_manager_instance = LoginManager(page)
        
        try:
            print("로그인 시도...")
            await login_manager_instance.login()
            if not login_manager_instance.is_logged_in:
                print("로그인에 실패하여 스크레이퍼 예제를 실행할 수 없습니다.")
                return
            print("로그인 성공!")

            scraper = Scraper(page, login_manager_instance)
            
            test_brns = ["1448121513", "1758100190"] # 정상, 비공개 예상
            target_years_to_scrape = ["2023", "2022", "2021"]

            for search_brn in test_brns:
                print(f"\n--- 사업자등록번호 '{search_brn}'으로 단일 기업 정보 스크랩 시도 ---")
                companies = await scraper.scrape_companies_with_financials(
                    search_query=search_brn,
                    target_years=target_years_to_scrape
                )
                if companies:
                    print(f"\n'{search_brn}'에 대한 최종 수집 정보:")
                    for company in companies:
                        print(f"  회사명: {company.name}")
                        print(f"  사업자등록번호: {company.business_registration_number}")
                        print(f"  대표자명: {company.ceo}")
                        print(f"  상태: {company.status}")
                        print(f"  재무정보: {company.financials}")
                        if company.html_snapshot_path:
                            print(f"  HTML 스냅샷: {company.html_snapshot_path}")
                else:
                    print(f"'{search_brn}'에 대한 정보를 수집하지 못했거나 처리 중 오류 발생 (결과 리스트 비어있음).")
                print("--- 스크랩 시도 완료 ---")
                await asyncio.sleep(2) # 다음 검색 전 잠시 대기

        except LoginError as e:
            print(f"로그인 중 LoginError 발생: {e}")
        except ScrapingError as e:
            print(f"스크래핑 중 ScrapingError 발생: {e}")
        except Exception as e:
            print(f"예상치 못한 오류 발생 (in example_scraper_usage): {e}")
            import traceback
            print(traceback.format_exc())
        finally:
            if 'login_manager_instance' in locals() and login_manager_instance.is_logged_in:
                 print("\nLoginManager 예제 사용 종료 전 로그아웃 시도...")
                 await login_manager_instance.logout()
            print("\nScraper 예제 사용 종료.")

if __name__ == "__main__":
    asyncio.run(example_scraper_usage()) 