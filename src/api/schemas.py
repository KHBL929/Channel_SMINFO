from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class FinancialInfo(BaseModel):
    """개별 연도의 재무 정보를 나타내는 Pydantic 모델 (응답의 일부)
       PRD FR-008 응답의 financials 내부 키들을 동적으로 처리하기 위해
       여기는 구체적인 연도별 필드 대신 Dict를 사용할 수 있지만,
       명시적인 필드가 타입 검증에 더 유리할 수 있습니다.
       일단은 PRD 예시처럼 키가 "YYYY_revenue", "YYYY_operating_profit" 형태라고 가정하고
       CompanyFinancialsResponse에서 Dict[str, Optional[float]] 형태로 처리합니다.
    """
    # 예시: 만약 고정된 연도만 다룬다면 아래처럼 명시적 필드 선언 가능
    # revenue_2024: Optional[float] = Field(None, description="2024년 매출액")
    # operating_profit_2024: Optional[float] = Field(None, description="2024년 영업이익")
    # ...
    # 여기서는 CompanyFinancialsResponse.financials 에서 Dict로 처리하므로 별도 필드 불필요
    pass # 실제 사용은 CompanyFinancialsResponse.financials 에서 이루어짐

class CompanyFinancialsResponse(BaseModel):
    """사업자등록번호 기반 기업 재무 정보 조회 API의 성공 응답 모델 (PRD FR-008)"""
    business_registration_number: str = Field(..., description="사업자등록번호", example="123-45-67890")
    company_name: Optional[str] = Field(None, description="회사명 (크롤링 가능 시)", example="주식회사 예시")
    ceo: Optional[str] = Field(None, description="대표자명 (크롤링 가능 시)", example="홍길동")
    status: str = Field(default="정보없음", description="기업 정보 상태 (예: 정상, 정보없음, 오류)", example="정상")
    # data_available_years: List[str] = Field(default_factory=list, description="실제 데이터가 있는 연도 목록", example=["2023", "2022"])
    # financials는 연도와 항목(revenue/operating_profit) 조합을 키로 가짐
    # 예: {"2023_revenue": 1000000000, "2023_operating_profit": 100000000, ...}
    # 값은 float 또는 int가 될 수 있고, 없을 경우 해당 키가 없거나 값이 None일 수 있음.
    # FastAPI는 자동으로 float을 int로 변환하지 않으므로, 숫자형 데이터는 float으로 통일하는 것이 좋음.
    financials: Dict[str, Optional[float]] = Field(default_factory=dict, description="연도별 재무 상세 정보")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "business_registration_number": "123-45-67890",
                    "company_name": "주식회사 예시",
                    "ceo": "홍길동",
                    "status": "정상",
                    # "data_available_years": ["2024", "2023", "2022"],
                    "financials": {
                        "2024_revenue": 1200000000.0,
                        "2024_operating_profit": 120000000.0,
                        "2023_revenue": 1100000000.0,
                        "2023_operating_profit": 110000000.0,
                        "2022_revenue": 1000000000.0,
                        "2022_operating_profit": 100000000.0
                    }
                },
                {
                    "business_registration_number": "987-65-43210",
                    "company_name": "주식회사 다른예시",
                    "ceo": "고길동",
                    "status": "정보없음 (재무)",
                    # "data_available_years": ["2023"],
                    "financials": {
                        "2023_revenue": 900000000.0,
                        "2023_operating_profit": 80000000.0
                    }
                }
            ]
        }

class ErrorDetail(BaseModel):
    loc: Optional[List[str]] = None
    msg: str
    type: Optional[str] = None

class HTTPErrorResponse(BaseModel):
    """API 오류 발생 시 공통 응답 모델"""
    detail: Any # FastAPI의 HTTPException detail과 형식을 맞추거나, ErrorDetail 리스트 사용 가능
    # 예시: detail: str = Field(..., description="오류 메시지")
    # 예시: detail: List[ErrorDetail] = Field(..., description="상세 오류 정보")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "detail": "요청한 사업자등록번호(000-00-00000)에 해당하는 기업을 찾을 수 없습니다."
                },
                {
                    "detail": [
                        {
                            "loc": ["path", "business_registration_number"],
                            "msg": "Field required",
                            "type": "missing"
                        }
                    ]
                }
            ]
        }

# 만약 API 요청 시 query parameter나 request body가 있다면 여기에 모델을 정의합니다.
# class CompanyFinancialsParams(BaseModel):
#     target_years: Optional[List[str]] = Field(None, description="조회 대상 연도 (미지정 시 기본값 사용)") 