from fastapi import APIRouter, Path, HTTPException, status, Depends
from typing import Annotated, List, Optional

from src.api.schemas import CompanyFinancialsResponse, HTTPErrorResponse # Pydantic 모델 임포트
from src.crawler.browser import BrowserManager
from src.crawler.login import LoginManager, LoginError
from src.crawler.scraper import Scraper, ScrapingError, CompanyData
from src.crawler.config import settings
import re

# User-Agent 및 Viewport 상수 정의
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
VIEWPORT = {"width": 1920, "height": 1080}

router = APIRouter(
    prefix="/api/v1/company-financials",
    tags=["Company Financials"], # Swagger UI 태그
)

# --- 의존성 주입 (Dependency Injection) 설정 예시 --- 
# 애플리케이션 생애주기 동안 BrowserManager 인스턴스를 관리하고 싶을 수 있습니다.
# 여기서는 간단한 예시로, 실제로는 main.py에서 앱 시작/종료 시 관리하는 것이 더 일반적입니다.
# async def get_browser_manager(): # 실제로는 BrowserManager 초기화/반환 로직 필요
#     # 이 함수는 요청마다 호출될 수 있으므로, BrowserManager를 재사용하는 전략이 필요합니다.
#     # 예: 글로벌 변수, FastAPI의 app.state, 또는 외부 라이브러리(fastapi-utils의 repeat_every 등) 활용
#     # 지금은 더미 구현
#     pass 

# async def get_scraper(page: Annotated[Page, Depends(get_page_from_browser_manager)]):
#     return Scraper(page)
# -----------------------------------------------------

# 정규표현식으로 사업자등록번호 형식 검증 (하이픈 포함/미포함, 숫자 10자리)
# 예: 123-45-67890 또는 1234567890
# Path(...)의 regex는 FastAPI 0.95.0 이상에서 지원
BRN_REGEX = r"^(\d{3}-?\d{2}-?\d{5})$"

@router.get(
    "/{business_registration_number}", 
    response_model=CompanyFinancialsResponse,
    summary="사업자등록번호로 기업 재무 정보 조회",
    description="제공된 사업자등록번호를 사용하여 SMINFO에서 해당 기업의 정보를 크롤링하여 반환합니다.",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": HTTPErrorResponse, "description": "잘못된 요청 (예: 사업자등록번호 형식 오류)"},
        status.HTTP_404_NOT_FOUND: {"model": HTTPErrorResponse, "description": "기업 정보를 찾을 수 없음"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": HTTPErrorResponse, "description": "서버 내부 오류 (크롤링 실패 등)"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HTTPErrorResponse, "description": "SMINFO 서비스 또는 로그인 일시적 사용 불가"},
    }
)
async def get_company_financials_by_brn(
    business_registration_number: Annotated[str, Path(
        description="조회할 기업의 사업자등록번호 (예: 123-45-67890 또는 1234567890)",
        example="1448121513",
    )]
):
    """
    사업자등록번호를 기반으로 기업의 재무 정보를 조회합니다 (PRD FR-008).
    
    - **business_registration_number**: 조회할 기업의 사업자등록번호. 하이픈은 포함하거나 제외할 수 있습니다.
    """
    
    if not re.match(BRN_REGEX, business_registration_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 사업자등록번호 형식입니다: '{business_registration_number}'. 형식: 000-00-00000 또는 0000000000"
        )

    normalized_brn = business_registration_number.replace("-", "")
    print(f"API 요청 수신: 사업자등록번호 {normalized_brn} (원본: {business_registration_number})")

    if not settings.SMINFO_ID or "default_id" in settings.SMINFO_ID or \
       not settings.SMINFO_PW or "default_pw" in settings.SMINFO_PW:
        print("API Error: SMINFO_ID 또는 SMINFO_PW가 .env 파일에 설정되지 않았습니다.")
        # 실제 운영 환경에서는 사용자에게 상세 ID/PW 오류를 노출하지 않는 것이 좋습니다.
        # 여기서는 개발 편의를 위해 구체적인 메시지를 포함하지만, 실제로는 일반적인 서버 오류로 처리할 수 있습니다.
        raise HTTPException(status_code=503, detail="서비스 설정을 불러올 수 없습니다. SMINFO 접속 정보가 누락되었습니다.")

    company_data_obj: CompanyData | None = None
    # headful_mode = False # API에서는 항상 headless=True를 기본으로 사용
    # if os.getenv("RUN_API_HEADFUL", "False").lower() == "true":
    #     print("API가 Headful 모드로 실행됩니다 (디버깅용).")
    #     headful_mode = True

    try:
        # BrowserManager, LoginManager, Scraper 인스턴스화
        async with BrowserManager(headless=True) as bm: # API는 항상 headless=True
            page = await bm.new_page(user_agent=USER_AGENT, viewport=VIEWPORT) # User-Agent, Viewport 설정 추가
            
            login_manager = LoginManager(page) # LoginManager 생성

            print("SMINFO 로그인 시도...")
            try:
                await login_manager.login()
                if not login_manager.is_logged_in:
                    # LoginError가 login() 내부에서 발생하므로, 실제로는 이 조건에 도달하기 어려울 수 있음
                    print("API Error: SMINFO 로그인 실패 (is_logged_in False)")
                    raise HTTPException(status_code=503, detail="SMINFO 서비스에 로그인할 수 없습니다.")
            except LoginError as e:
                print(f"API Error: SMINFO 로그인 중 LoginError 발생: {e}")
                # 로그인 실패 시 스냅샷을 찍고 싶다면 여기서 page 객체 사용 가능
                # await page.screenshot(path="api_login_failure.png")
                raise HTTPException(status_code=503, detail=f"SMINFO 서비스 로그인 실패: {e}")
            
            print("SMINFO 로그인 성공. 정보 스크래핑 시작...")
            scraper = Scraper(page, login_manager) # Scraper 생성 시 login_manager 전달
            
            # 변경: 모든 연도의 데이터를 가져오기 위해 target_years를 None으로 설정
            target_years = None
            
            print(f"기업 정보 스크래핑 시작 (BRN: {normalized_brn})...")
            companies_data_list = await scraper.scrape_companies_with_financials(
                search_query=normalized_brn,
                search_type="business_registration_number",
                target_years=target_years 
            )
            print(f"스크래핑 완료 (BRN: {normalized_brn}). 결과 수: {len(companies_data_list)}")

            if not companies_data_list:
                print(f"기업 정보를 찾을 수 없음 (결과 리스트 비어있음) (BRN: {normalized_brn})")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"사업자등록번호 '{normalized_brn}'에 해당하는 기업 정보를 SMINFO에서 찾을 수 없거나 스크래핑 중 오류가 발생했습니다."
                )
            
            company_data: CompanyData = companies_data_list[0]
            print(f"추출된 CompanyData (BRN: {normalized_brn}): {company_data}")

            if "오류" in company_data.status or company_data.status == "정보없음 (검색결과없음)":
                if company_data.status == "정보없음 (검색결과없음)":
                    print(f"기업 정보 없음 (검색결과없음 상태) (BRN: {normalized_brn})")
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"사업자등록번호 '{normalized_brn}'으로 SMINFO에서 기업을 찾을 수 없었습니다."
                    )
                elif "오류" in company_data.status : 
                    print(f"스크래핑 오류 상태 반환 (BRN: {normalized_brn}): {company_data.status}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"기업 정보 처리 중 서버 내부 오류 발생 (상태: {company_data.status}). 잠시 후 다시 시도해주세요."
                    )
            
            print(f"API 응답 생성 (BRN: {normalized_brn}): {company_data}")
            return CompanyFinancialsResponse(
                business_registration_number=company_data.business_registration_number or normalized_brn,
                company_name=company_data.name,
                ceo=company_data.ceo,
                status=company_data.status,
                financials=company_data.financials
            )

    except ScrapingError as se:
        print(f"ScrapingError 발생 (API 레벨) (BRN: {normalized_brn}): {se}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"기업 정보 조회 중 오류 발생: {se}. 잠시 후 다시 시도해주세요."
        )
    except HTTPException as http_exc: 
        raise http_exc
    except Exception as e:
        print(f"예상치 못한 API 오류 발생 (BRN: {normalized_brn}): {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"서버 내부에서 예상치 못한 오류가 발생했습니다. 관리자에게 문의하세요."
        )