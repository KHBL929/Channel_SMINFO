import asyncio
import os
from playwright.async_api import Page, Dialog, TimeoutError as PlaywrightTimeoutError
from src.crawler.config import settings # 설정 파일에서 ID/PW, URL, 선택자 등 가져오기
# from src.crawler.browser import BrowserManager # LoginManager가 직접 BrowserManager를 소유하지 않는다면 주석 처리

# SMINFO 웹사이트의 실제 선택자는 Selector.md 또는 config.py 에서 관리/참조해야 합니다.
# 아래는 예시 선택자입니다.
# LOGIN_PAGE_URL_FALLBACK = settings.SMINFO_LOGIN_URL # config.py에서 가져오거나 여기서 직접 정의
# 직접 로그인 페이지 이동이 막혔으므로 위 상수는 사용하지 않거나, 로그인 성공 후 리다이렉션 검증용으로 사용 가능

MAIN_PAGE_LOGIN_LINK_SELECTOR = "#wrap > div.header.clearfix > div.global_box > ul > li:nth-child(2) > a" # 사용자 제공 선택자

ID_INPUT_SELECTOR = '#id'                                                                                          # Selector.md 반영
PW_INPUT_SELECTOR = '#pwd'                                                                                         # Selector.md 반영
LOGIN_BUTTON_SELECTOR = '#contents_sub > div:nth-child(3) > div > div.login_lr_box.clearfix > div.lr_text_r > div:nth-child(1) > form > button > span' # Selector.md 반영
LOGOUT_BUTTON_SELECTOR = '#main_link > div > div.main_login_box.m_main_login_box > div > form > fieldset > div > button > span' # Selector.md 반영
# 로그인 성공 시 이동하는 특정 URL 또는 페이지 내 요소로도 판단 가능

class LoginError(Exception):
    """로그인 과정에서 발생하는 특정 에러"""
    pass

class LoginManager:
    """
    SMINFO 웹사이트 로그인을 관리합니다.
    주어진 Page 객체를 사용하여 로그인 절차를 수행하고, 로그인 상태를 확인합니다.
    """
    def __init__(self, page: Page):
        """
        LoginManager를 초기화합니다.

        Args:
            page (Page): Playwright의 Page 객체. 이 페이지를 사용하여 로그인합니다.
        """
        self.page = page
        self.is_logged_in = False
        self._login_attempt_count = 0
        self._dialog_message_for_login_failure: str | None = None
        self._login_dialog_handler_active = False # 중복 리스너 방지용 플래그

    async def _handle_login_dialog(self, dialog: Dialog):
        """로그인 시도 중 발생하는 다이얼로그 처리"""
        print(f"로그인/검증 중 팝업 발견: Type={dialog.type}, Message='{dialog.message}'")
        self._dialog_message_for_login_failure = dialog.message
        await dialog.dismiss()
        print("팝업 자동 닫기 완료.")

    def _ensure_dialog_handler(self):
        if not self._login_dialog_handler_active:
            self.page.on("dialog", self._handle_login_dialog)
            self._login_dialog_handler_active = True
            print("다이얼로그 핸들러 활성화됨.")

    def _remove_dialog_handler(self):
        if self._login_dialog_handler_active:
            try:
                self.page.remove_listener("dialog", self._handle_login_dialog)
                self._login_dialog_handler_active = False
                print("다이얼로그 핸들러 비활성화됨.")
            except Exception as e:
                # 이미 제거되었거나 다른 이유로 실패할 수 있음 (특히 페이지 닫힘 등)
                print(f"다이얼로그 핸들러 제거 중 오류 (무시 가능): {e}")
                self._login_dialog_handler_active = False # 어쨌든 비활성으로 표시

    async def login(self):
        if self.is_logged_in:
            print("이미 로그인된 상태입니다. (is_logged_in 플래그 기준)")
            if await self.check_login_status(force_check=True): # 실제 상태 재확인
                print("check_login_status 재확인 결과: 로그인 상태 유지됨.")
                return
            else:
                print("경고: is_logged_in=True였으나 check_login_status=False. 로그아웃된 상태로 간주하고 로그인 진행.")
                self.is_logged_in = False
        
        self._ensure_dialog_handler()
        self._login_attempt_count = 0

        try:
            while self._login_attempt_count < settings.MAX_LOGIN_ATTEMPTS:
                self._login_attempt_count += 1
                self._dialog_message_for_login_failure = None
                print(f"--- 로그인 시도 #{self._login_attempt_count}/{settings.MAX_LOGIN_ATTEMPTS} ---")

                try:
                    print(f"메인 페이지({settings.SMINFO_MAIN_PAGE_URL})로 이동 시도...")
                    await self.page.goto(settings.SMINFO_MAIN_PAGE_URL, wait_until="networkidle", timeout=30000)
                    print("메인 페이지로 이동 완료.")
                    await asyncio.sleep(settings.DEFAULT_SLEEP_TIME_SHORT)

                    # 메인 페이지에서 "로그인" 링크 클릭하여 로그인 페이지로 이동
                    print(f"메인 페이지의 로그인 링크 클릭 시도: {settings.MAIN_PAGE_LOGIN_LINK_SELECTOR}")
                    async with self.page.expect_navigation(wait_until="domcontentloaded", timeout=15000): # 로그인 페이지 로드 기다림
                        await self.page.locator(settings.MAIN_PAGE_LOGIN_LINK_SELECTOR).click()
                    print(f"로그인 링크 클릭 후, 현재 URL: {self.page.url} (예상: 로그인 페이지)")
                    
                    # ID/PW 입력 필드 확인
                    await self.page.wait_for_selector(settings.SMINFO_ID_INPUT_SELECTOR, timeout=15000, state="visible")
                    print(f"로그인 페이지로 이동 확인됨 (ID 입력 필드 '{settings.SMINFO_ID_INPUT_SELECTOR}' 확인).")

                    await self.page.fill(settings.SMINFO_ID_INPUT_SELECTOR, settings.SMINFO_ID)
                    print(f"ID 입력 완료: {settings.SMINFO_ID_INPUT_SELECTOR}")
                    await self.page.fill(settings.SMINFO_PW_INPUT_SELECTOR, settings.SMINFO_PW)
                    print(f"PW 입력 완료: {settings.SMINFO_PW_INPUT_SELECTOR}")
                    await asyncio.sleep(settings.DEFAULT_SLEEP_TIME_VERY_SHORT)

                    # 로그인 페이지의 "로그인" 버튼 클릭
                    print(f"로그인 페이지의 로그인 버튼({settings.SMINFO_LOGIN_BUTTON_SELECTOR}) 클릭 시도...")
                    navigated_after_login_click = False
                    try:
                        async with self.page.expect_navigation(wait_until="networkidle", timeout=20000): # 로그인 후 페이지 이동 대기
                            await self.page.click(settings.SMINFO_LOGIN_BUTTON_SELECTOR, timeout=10000) # 버튼 클릭 자체의 타임아웃
                        navigated_after_login_click = True
                        print(f"로그인 버튼 클릭 및 네비게이션 완료. 현재 URL: {self.page.url}")
                    except PlaywrightTimeoutError as e_nav:
                        print(f"로그인 버튼 클릭 후 네비게이션 타임아웃: {e_nav}. 현재 URL: {self.page.url}")
                        # 네비게이션 타임아웃이어도, 팝업이 뜨거나 페이지 내 변화가 있을 수 있음
                        # 또는 이미 로그인된 상태로 페이지가 그대로일 수도 (매우 드묾)
                        pass # 아래에서 팝업 및 서비스 접근 검증 진행
                    
                    # 팝업 발생 여부 확인
                    if self._dialog_message_for_login_failure:
                        print(f"로그인 실패 팝업 메시지 감지: '{self._dialog_message_for_login_failure}'")
                        await self._save_login_attempt_snapshot(f"login_failed_popup_detected_{self._login_attempt_count}")
                        await asyncio.sleep(settings.DEFAULT_SLEEP_TIME_MEDIUM)
                        continue # 다음 로그인 시도

                    # 서비스 접근을 통한 최우선 검증
                    print("로그인 후 서비스 접근 검증 시도...")
                    if await self._verify_login_via_service_access():
                        print("서비스 접근 검증 성공! 최종 로그인 성공으로 간주.")
                        self.is_logged_in = True
                        # 로그인 성공 후, 부차적으로 버튼 텍스트 확인 (로깅용)
                        try:
                            current_text = await self.page.locator(settings.LOGOUT_BUTTON_SELECTOR).text_content(timeout=2000)
                            print(f"로그인 성공 후 버튼 텍스트 (참고용): '{current_text}'")
                        except Exception:
                            print("로그인 성공 후 버튼 텍스트 확인 실패 (무시).")
                        return # 로그인 성공, 전체 메서드 종료
                    else:
                        print("서비스 접근 검증 실패. 로그인 실패로 간주.")
                        await self._save_login_attempt_snapshot(f"login_service_access_failed_{self._login_attempt_count}")
                        # UI 텍스트 변경 여부도 추가로 확인해볼 수 있으나, 서비스 접근 실패 시 큰 의미 없음
                        # 이 시점에서 UI 텍스트가 "로그아웃"으로 되어있다고 해도 실제 세션은 없을 가능성 높음
                        current_text_fallback = "알수없음"
                        try:
                            current_text_fallback = await self.page.locator(settings.LOGOUT_BUTTON_SELECTOR).text_content(timeout=1000)
                        except Exception:
                            pass
                        print(f"서비스 접근 실패 시 버튼 텍스트 (참고용): {current_text_fallback}")
                        await asyncio.sleep(settings.DEFAULT_SLEEP_TIME_MEDIUM)
                        continue # 다음 로그인 시도
                
                except PlaywrightTimeoutError as e_timeout:
                    print(f"로그인 시도 #{self._login_attempt_count} 중 주요 단계에서 타임아웃 발생: {e_timeout}")
                    if not self.page.is_closed():
                        await self._save_login_attempt_snapshot(f"login_major_timeout_{self._login_attempt_count}")
                except Exception as e_general:
                    print(f"로그인 시도 #{self._login_attempt_count} 중 예외 발생: {e_general}")
                    import traceback
                    print(traceback.format_exc())
                    if not self.page.is_closed():
                        await self._save_login_attempt_snapshot(f"login_attempt_exception_{self._login_attempt_count}_{type(e_general).__name__}")
                
                # 루프의 마지막 (재시도 전)
                print(f"로그인 시도 #{self._login_attempt_count} 실패. 다음 시도까지 {settings.DEFAULT_SLEEP_TIME_MEDIUM}초 대기...")
                await asyncio.sleep(settings.DEFAULT_SLEEP_TIME_MEDIUM)

            # 모든 로그인 시도 실패
            if not self.is_logged_in:
                raise LoginError(f"{settings.MAX_LOGIN_ATTEMPTS}번의 로그인 시도 후 최종 실패.")
        finally:
            self._remove_dialog_handler()

    async def _verify_login_via_service_access(self) -> bool:
        """로그인 후 실제 회원 전용 서비스 접근을 통해 로그인 상태를 검증합니다."""
        print("로그인 검증 시작: 실제 회원 전용 서비스 접근 시도...")
        self._ensure_dialog_handler() # 검증 중에도 팝업 발생 가능
        original_url = self.page.url
        snapshot_prefix = "login_verification"

        try:
            if not self.page.url.startswith(settings.SMINFO_MAIN_PAGE_URL.split('?')[0]):
                print(f"검증: 현재 메인 페이지 아님 ({self.page.url}). 메인 페이지로 이동.")
                await self.page.goto(settings.SMINFO_MAIN_PAGE_URL, wait_until="networkidle", timeout=15000)
                await asyncio.sleep(settings.DEFAULT_SLEEP_TIME_VERY_SHORT)
            
            gnb_main_menu_locator = self.page.locator(settings.GNB_MENU_FIRST_LEVEL_SELECTOR)
            await gnb_main_menu_locator.wait_for(state="visible", timeout=10000)
            await gnb_main_menu_locator.click(timeout=5000)
            print(f"검증: GNB 1차 메뉴({settings.GNB_MENU_FIRST_LEVEL_SELECTOR}) 클릭 완료.")
            await asyncio.sleep(0.8)

            gnb_submenu_locator = self.page.locator(settings.GNB_MENU_SECOND_LEVEL_SELECTOR)
            await gnb_submenu_locator.wait_for(state="visible", timeout=10000)
            print(f"검증: GNB 2차 메뉴({settings.GNB_MENU_SECOND_LEVEL_SELECTOR}) 클릭 시도...")
            await gnb_submenu_locator.click(timeout=5000)
            print("검증: GNB 2차 메뉴 클릭 완료.")
            await asyncio.sleep(settings.DEFAULT_SLEEP_TIME_SHORT)

            if self._dialog_message_for_login_failure and "회원전용" in self._dialog_message_for_login_failure:
                print(f"로그인 검증 실패: GNB 메뉴 클릭 후 '회원전용 서비스' 팝업 감지 ('{self._dialog_message_for_login_failure}').")
                if not self.page.is_closed():
                    await self._save_login_attempt_snapshot(f"{snapshot_prefix}_popup_detected")
                return False

            try:
                await self.page.wait_for_selector(settings.SEARCH_TEXT_INPUT_SELECTOR, timeout=15000, state="visible")
                print(f"로그인 검증 성공: GNB 메뉴 클릭 후 검색 입력 필드({settings.SEARCH_TEXT_INPUT_SELECTOR}) 확인.")
                if not self.page.is_closed():
                    await self._save_login_attempt_snapshot(f"{snapshot_prefix}_search_input_found")
                return True
            except PlaywrightTimeoutError:
                print(f"로그인 검증 실패: GNB 메뉴 클릭 후 검색 입력 필드({settings.SEARCH_TEXT_INPUT_SELECTOR}) 대기 시간 초과.")
                print(f"검증 실패 시 현재 URL: {self.page.url}")
                if not self.page.is_closed():
                    await self._save_login_attempt_snapshot(f"{snapshot_prefix}_search_input_timeout")
                return False
        except Exception as e:
            print(f"로그인 검증 중 예외 발생: {e}")
            import traceback
            print(traceback.format_exc())
            if not self.page.is_closed():
                 await self._save_login_attempt_snapshot(f"{snapshot_prefix}_exception_{type(e).__name__}")
            return False
        # _verify_login_via_service_access는 자체적으로 핸들러를 제거하지 않고, 호출한 login 메서드에서 관리.

    async def check_login_status(self, force_check: bool = False) -> bool:
        if not force_check and self.is_logged_in:
            return True
        
        print("로그인 상태 확인 중 (UI 버튼 텍스트 및 서비스 접근 검증 시도)...")
        self._ensure_dialog_handler()
        try:
            # 1. UI 버튼 텍스트로 빠른 확인
            is_logged_in_by_ui = False
            try:
                if not self.page.url.startswith(settings.SMINFO_MAIN_PAGE_URL.split('?')[0]):
                    await self.page.goto(settings.SMINFO_MAIN_PAGE_URL, wait_until="domcontentloaded", timeout=10000)
                login_box_button = self.page.locator(settings.LOGIN_BOX_LOGIN_BUTTON_SELECTOR)
                await login_box_button.wait_for(state="visible", timeout=5000)
                logout_span_locator = self.page.locator(settings.LOGOUT_BUTTON_SELECTOR)
                text_content = await logout_span_locator.text_content(timeout=3000)
                if text_content == settings.LOGGED_IN_TEXT_INDICATOR:
                    print(f"UI 상태 확인: 버튼 텍스트 '{settings.LOGGED_IN_TEXT_INDICATOR}' (로그인 상태로 보임).")
                    is_logged_in_by_ui = True
                else:
                    print(f"UI 상태 확인: 버튼 텍스트 '{text_content}' (로그아웃 상태로 보임).")
            except Exception as e_ui_check:
                print(f"UI 상태 확인 중 오류 (무시하고 서비스 접근 검증 진행): {e_ui_check}")

            # 2. 실제 서비스 접근으로 최종 확인 (UI와 관계없이 중요)
            print("check_login_status: 서비스 접근을 통한 추가 검증 시도...")
            is_logged_in_by_service = await self._verify_login_via_service_access()
            
            if is_logged_in_by_service:
                print("check_login_status: 서비스 접근 가능. 최종 로그인 상태로 판단.")
                self.is_logged_in = True
                return True
            else:
                print("check_login_status: 서비스 접근 불가. 최종 로그아웃 상태로 판단.")
                # UI가 로그인 상태로 보였더라도, 서비스 접근이 안되면 로그아웃으로 간주
                if is_logged_in_by_ui:
                    print("경고: UI는 로그인 상태로 보였으나, 실제 서비스 접근은 실패했습니다.")
                self.is_logged_in = False
                return False

        except Exception as e:
            print(f"check_login_status 중 예외 발생: {e}")
            self.is_logged_in = False
            return False
        finally:
            self._remove_dialog_handler()

    async def logout(self):
        print("로그아웃 시도...")
        if not await self.check_login_status(force_check=True):
            print("check_login_status 결과, 이미 로그아웃된 상태입니다. 로그아웃 절차를 건너니다.")
            self.is_logged_in = False
            return

        self._ensure_dialog_handler()
        try:
            logout_button_element = self.page.locator(settings.LOGIN_BOX_LOGIN_BUTTON_SELECTOR)
            print(f"로그아웃 버튼({settings.LOGIN_BOX_LOGIN_BUTTON_SELECTOR}) 클릭 시도...")
            
            async with self.page.expect_navigation(url=lambda u: u.startswith(settings.SMINFO_MAIN_PAGE_URL.split('?')[0]), wait_until="networkidle", timeout=20000):
                await logout_button_element.click(timeout=10000)
            print("로그아웃 버튼 클릭 및 메인 페이지 네비게이션 확인됨.")
            self.is_logged_in = False

            await asyncio.sleep(settings.DEFAULT_SLEEP_TIME_SHORT)
            try:
                login_box_button = self.page.locator(settings.LOGIN_BOX_LOGIN_BUTTON_SELECTOR)
                await login_box_button.wait_for(state="visible", timeout=5000)
                current_text_in_span = await self.page.locator(settings.LOGOUT_BUTTON_SELECTOR).text_content(timeout=5000)
                if current_text_in_span != settings.LOGGED_IN_TEXT_INDICATOR:
                    print(f"로그아웃 후 버튼 텍스트 변경 확인 (기대: '{settings.LOGGED_IN_TEXT_INDICATOR}'가 아님, 실제: '{current_text_in_span}').")
                else:
                    print(f"경고: 로그아웃 후 버튼 텍스트가 여전히 '{settings.LOGGED_IN_TEXT_INDICATOR}'입니다. 확인 필요.")
            except Exception as e_text_check:
                print(f"로그아웃 후 버튼 텍스트 확인 중 오류: {e_text_check}. 로그아웃은 된 것으로 간주.")

        except PlaywrightTimeoutError as e:
            print(f"로그아웃 중 타임아웃 발생: {e}. 로그아웃 상태 불확실.")
            self.is_logged_in = False
            if not self.page.is_closed():
                await self._save_login_attempt_snapshot("logout_timeout")
        except Exception as e:
            print(f"로그아웃 중 예외 발생: {e}")
            import traceback
            print(traceback.format_exc())
            self.is_logged_in = False
            if not self.page.is_closed():
                await self._save_login_attempt_snapshot(f"logout_exception_{type(e).__name__}")
        finally:
            self._remove_dialog_handler()

    async def _save_login_attempt_snapshot(self, prefix: str):
        """로그인 시도 중 특정 상황에서 HTML 스냅샷 저장"""
        if not settings.SAVE_HTML_SNAPSHOTS:
            return
        try:
            import datetime # 함수 내에서 import 하도록 수정 (혹시 모를 NameError 방지)
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            snapshot_dir = settings.get_html_snapshot_path("login_attempts")
            os.makedirs(snapshot_dir, exist_ok=True)
            filename = f"{timestamp}_{prefix}.html"
            filepath = os.path.join(snapshot_dir, filename)
            if not self.page.is_closed():
                content = await self.page.content()
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"로그인/로그아웃 시도 중 HTML 스냅샷 저장: {filepath}")
            else:
                print(f"페이지가 닫혀 스냅샷 저장 불가: {prefix}")
        except Exception as e:
            print(f"스냅샷 저장 오류: {e}")

# LoginManager 사용 예시 (BrowserManager와 함께 사용)
async def example_login_manager_usage():
    from src.crawler.browser import BrowserManager
    # headless 모드 테스트를 위해 True로 변경
    async with BrowserManager(headless=True) as bm:
        page = await bm.new_page()
        login_manager = LoginManager(page)
        try:
            print("--- 로그인 시도 (Headless Mode) ---")
            await login_manager.login()
            if login_manager.is_logged_in:
                print("최종 로그인 상태: 성공")
                print("--- 현재 상태 확인 시도 --- ")
                await login_manager.check_login_status(force_check=True)
                print("--- 로그아웃 시도 --- ")
                await login_manager.logout()
                print(f"로그아웃 후 is_logged_in: {login_manager.is_logged_in}")
                print("--- 로그아웃 후 상태 재확인 --- ")
                is_still_logged_in_after_logout = await login_manager.check_login_status(force_check=True)
                print(f"로그아웃 후 최종 상태 확인 결과: {'로그인됨' if is_still_logged_in_after_logout else '로그아웃됨'}")
            else:
                print("최종 로그인 상태: 실패")
        except LoginError as e:
            print(f"LoginManager 사용 중 오류: {e}")
        except Exception as e:
            print(f"알 수 없는 오류 발생: {e}")
            import traceback
            print(traceback.format_exc())
        finally:
            print("LoginManager 예제 사용 종료 (Headless Mode).")

if __name__ == '__main__':
    try:
        asyncio.run(example_login_manager_usage())
    except Exception as e:
        print(f"LoginManager 실행 중 에러: {e}")
        import traceback
        print(traceback.format_exc())
        print("SMINFO ID/PW가 .env 파일에 정확히 설정되었는지, playwright install을 실행했는지 확인하세요.")
        print("또한, LOGIN_PAGE_URL_FALLBACK, ID_INPUT_SELECTOR 등의 선택자가 실제 SMINFO 사이트와 일치하는지 확인 필요합니다.") 