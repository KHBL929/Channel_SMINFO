from fastapi import FastAPI
from src.api.endpoints import company as company_router # company.py에서 router 객체 임포트
from src.crawler.config import settings # API 호스트, 포트 등 설정을 위함
import uvicorn # uvicorn 직접 실행을 위함 (if __name__ == "__main__")

# --- (선택적) 애플리케이션 생애주기 이벤트 핸들러 --- 
# 예: 앱 시작 시 Playwright BrowserManager 초기화, 종료 시 정리
# from src.crawler.browser import BrowserManager
# app_browser_manager = BrowserManager() # 전역 또는 app.state에 저장

# async def startup_event():
#     print("애플리케이션 시작: Playwright BrowserManager 초기화 시도...")
#     # await app_browser_manager.__aenter__() # BrowserManager를 싱글톤처럼 관리 시
#     # app.state.browser_manager = app_browser_manager 
#     # print("BrowserManager 초기화 완료.")
#     # 또는 요청 시마다 BrowserManager를 생성/소멸하는 방식도 가능 (Depends 사용)
#     pass

# async def shutdown_event():
#     print("애플리케이션 종료: Playwright BrowserManager 정리 시도...")
#     # if hasattr(app.state, 'browser_manager') and app.state.browser_manager:
#     #     await app.state.browser_manager.__aexit__(None, None, None)
#     #     print("BrowserManager 정리 완료.")
#     pass
# -----------------------------------------------------

app = FastAPI(
    title="SMINFO Crawler API",
    description="중소기업 현황정보 시스템(SMINFO)에서 기업 정보를 크롤링하고, 주요 재무 정보를 제공하는 API 입니다. (PRD 기반)",
    version="1.0.0",
    # on_startup=[startup_event], # 앱 시작 시 실행할 함수 리스트
    # on_shutdown=[shutdown_event]  # 앱 종료 시 실행할 함수 리스트
)

# API 라우터 포함
app.include_router(company_router.router)

@app.get("/", tags=["Root"], summary="API 루트 경로 Health Check")
async def read_root():
    """API 서버가 정상적으로 실행 중인지 간단히 확인합니다."""
    return {"message": "Welcome to SMINFO Crawler API!", "status": "ok"}


if __name__ == "__main__":
    # 이 파일이 직접 실행될 때 uvicorn 서버를 시작합니다.
    # 실제 배포 시에는 `uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload` 와 같이 CLI로 실행하는 것이 일반적입니다.
    print(f"Uvicorn 서버를 시작합니다: http://{settings.API_HOST}:{settings.API_PORT}")
    uvicorn.run("src.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True) 