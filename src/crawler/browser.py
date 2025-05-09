import asyncio
from playwright.async_api import async_playwright, Browser, Page, Playwright
# from src.crawler.config import settings # 아직 settings에 BROWSER_TYPE, HEADLESS_MODE 등이 없으므로 주석 처리

class BrowserManager:
    """
    Playwright 브라우저 인스턴스 및 페이지 객체를 관리합니다.
    async with 구문을 지원하여 브라우저의 자동 시작 및 종료를 보장합니다.

    사용 예시:
    async def main():
        async with BrowserManager() as browser_manager:
            page = await browser_manager.new_page()
            await page.goto("http://example.com")
            print(await page.title())
            # 브라우저와 페이지는 컨텍스트를 벗어나면 자동으로 닫힙니다.
    """
    def __init__(self, browser_type: str = "chromium", headless: bool = True):
        """
        BrowserManager를 초기화합니다.

        Args:
            browser_type (str): 사용할 브라우저 종류 ("chromium", "firefox", "webkit").
                                  # 향후 settings.BROWSER_TYPE 등으로 교체 가능
            headless (bool): 브라우저를 headless 모드로 실행할지 여부.
                               # 향후 settings.HEADLESS_MODE 등으로 교체 가능
        """
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self._browser_type_name: str = browser_type 
        self._headless: bool = headless
        self._pages: list[Page] = [] # 관리하는 페이지 목록

    async def __aenter__(self) -> 'BrowserManager':
        """비동기 컨텍스트 관리자 진입 시 호출됩니다. 브라우저를 시작합니다."""
        self.playwright = await async_playwright().start()
        browser_launcher = getattr(self.playwright, self._browser_type_name)
        if not browser_launcher:
            raise ValueError(f"Unsupported browser type: {self._browser_type_name}")
        
        launch_options = {"headless": self._headless}
        # 필요시 추가 옵션 (예: user_agent, viewport from settings)
        # launch_options["user_agent"] = settings.USER_AGENT 
        # launch_options["viewport"] = settings.VIEWPORT

        self.browser = await browser_launcher.launch(**launch_options)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 관리자 종료 시 호출됩니다. 모든 페이지와 브라우저를 닫습니다."""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        self._pages.clear() # 페이지 목록 초기화

    async def new_page(self, **kwargs) -> Page:
        """
        현재 브라우저 컨텍스트에서 새 페이지를 생성하여 반환합니다.
        생성된 페이지는 BrowserManager가 관리하며, 종료 시 함께 닫힙니다.

        Args:
            **kwargs: playwright page.new_context().new_page() 에 전달될 추가 옵션.
                      예: user_agent, viewport 등
        
        Returns:
            Page: 새로 생성된 Playwright Page 객체.
        
        Raises:
            RuntimeError: 브라우저가 초기화되지 않은 경우.
        """
        if not self.browser:
            raise RuntimeError("Browser is not initialized. Call within async with block.")
        
        # 기본 컨텍스트 옵션. 필요시 설정 파일 또는 인자로부터 받을 수 있습니다.
        context_options = {}
        # if settings.DEFAULT_USER_AGENT:
        #     context_options['user_agent'] = settings.DEFAULT_USER_AGENT
        # if settings.DEFAULT_VIEWPORT:
        #     context_options['viewport'] = settings.DEFAULT_VIEWPORT
        
        # kwargs로 전달된 값으로 context_options를 덮어쓸 수 있게 합니다.
        context_options.update(kwargs)

        context = await self.browser.new_context(**context_options)
        page = await context.new_page()
        self._pages.append(page) # 내부적으로 페이지 추적 (선택적)
        return page

    async def close_page(self, page: Page):
        """특정 페이지를 닫습니다."""
        if page in self._pages:
            self._pages.remove(page)
        if not page.is_closed():
            await page.close()

    async def close_all_pages(self):
        """관리 중인 모든 페이지를 닫습니다."""
        for page in list(self._pages): # 복사본 순회 (닫으면서 리스트 변경 방지)
            await self.close_page(page)

# 아래는 BrowserManager 사용 예시입니다.
async def example_usage():
    print("BrowserManager example usage started.")
    # 설정값을 사용하고 싶다면, settings 객체를 BrowserManager 생성자에 전달할 수 있습니다.
    # 예: async with BrowserManager(browser_type=settings.BROWSER_TYPE, headless=settings.HEADLESS_MODE) as bm:
    async with BrowserManager(headless=True) as bm: # 테스트를 위해 headless True로 실행
        page1 = await bm.new_page(user_agent="MyCustomUserAgent/1.0")
        await page1.goto("https://playwright.dev/python/")
        title1 = await page1.title()
        print(f"Page 1 Title: {title1}")
        # page1은 BrowserManager가 __aexit__에서 닫을 것이므로 명시적으로 닫을 필요는 없으나,
        # 개별적으로 닫고 싶다면 await bm.close_page(page1) 호출 가능

        # 다른 페이지도 생성 가능
        page2 = await bm.new_page()
        await page2.goto("https://www.python.org")
        title2 = await page2.title()
        print(f"Page 2 Title: {title2}")

    print("Browser and pages should be closed now.")
    # 여기서 bm.browser 와 bm.playwright 는 None이 됩니다.

if __name__ == "__main__":
    # Playwright는 GUI 이벤트 루프가 필요할 수 있으므로,
    # asyncio.run()을 직접 사용하는 것이 좋습니다.
    # Windows에서는 ProactorEventLoop가 필요할 수 있습니다.
    # if os.name == 'nt':
    # asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # `playwright install`을 먼저 실행해야 합니다.
    try:
        asyncio.run(example_usage())
    except Exception as e:
        print(f"An error occurred during example_usage: {e}")
        print("Please ensure you have run 'playwright install' first.") 