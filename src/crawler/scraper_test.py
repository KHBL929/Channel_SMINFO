from playwright.async_api import Page
import logging
from bs4 import BeautifulSoup
import pandas as pd

logger = logging.getLogger(__name__)

async def search_company_name(page: Page, company_name: str) -> bool:
    """회사명으로 검색"""
    try:
        # 검색어 입력
        await page.fill('#searchTxt', company_name)
        
        # 검색 버튼 클릭
        await page.click('#searchBtn')
        await page.wait_for_load_state('networkidle')
        
        return True
    except Exception as e:
        logger.error(f"회사명 검색 중 오류 발생: {str(e)}")
        return False

async def extract_company_info(page: Page) -> dict:
    """회사 정보 추출"""
    try:
        # 검색 결과 테이블 대기
        await page.wait_for_selector('table.table_list')
        
        # 회사 정보 추출
        company_info = {}
        
        # 회사명
        company_name = await page.text_content('table.table_list tr:first-child td:nth-child(2)')
        company_info["회사명"] = company_name.strip() if company_name else ""
        
        # 대표자명
        ceo_name = await page.text_content('table.table_list tr:first-child td:nth-child(3)')
        company_info["대표자명"] = ceo_name.strip() if ceo_name else ""
        
        # 사업자등록번호
        business_number = await page.text_content('table.table_list tr:first-child td:nth-child(4)')
        company_info["사업자등록번호"] = business_number.strip() if business_number else ""
        
        # 주소
        address = await page.text_content('table.table_list tr:first-child td:nth-child(5)')
        company_info["주소"] = address.strip() if address else ""
        
        return company_info
        
    except Exception as e:
        logger.error(f"회사 정보 추출 중 오류 발생: {str(e)}")
        return None

async def extract_sales_profit(page: Page, company_name: str = None) -> dict:
    """매출현황 테이블에서 매출액과 영업이익 데이터를 추출합니다."""
    try:
        # 매출현황 테이블 렌더링 대기 (최대 2초)
        await page.wait_for_selector('table.list_table.type02', timeout=2000)
        
        # 현재 페이지의 HTML 가져오기
        html_content = await page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 검색된 회사명 추출
        searched_company_title = soup.select_one('#contents_sub > div:nth-child(3) > div > h4.table_title')
        searched_company_name = ""
        if searched_company_title:
            searched_company_name = searched_company_title.text.strip()
            logger.info(f"검색된 회사명: {searched_company_name}")
        
        # 데이터 추출 결과 초기화
        result = {}
        if company_name:
            result['회사명 또는 사업자번호'] = company_name
        
        # 검색된 실제 회사명 추가
        if searched_company_name:
            result['검색된 회사명'] = searched_company_name
            
        # 매출현황 정보가 없는지 확인
        no_data_msg = soup.find(text="매출현황 정보가 없습니다.")
        if no_data_msg:
            logger.warning("매출현황 정보가 없습니다.")
            # 회사명 정보만 있어도 반환
            if len(result) > 0:
                result['검색완료'] = 'Y'  # 검색은 완료됨
                return result
            return None
        
        # 매출현황 테이블 찾기
        tables = soup.find_all('table', {'class': ['list_table', 'type02']})
        sales_table = None
        
        for table in tables:
            caption = table.find('caption')
            if caption and caption.text.strip() == '매출현황':
                sales_table = table
                break
        
        if not sales_table:
            logger.error("매출현황 테이블을 찾을 수 없습니다.")
            # 회사명 정보만 있어도 반환
            if len(result) > 0:
                result['검색완료'] = 'Y'  # 검색은 완료됨
                return result
            return None
        
        rows = sales_table.find_all('tr')[1:]  # 헤더 제외
        logger.info(f"매출현황 테이블에서 {len(rows)}개의 행을 찾았습니다.")
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 7:  # 결산년도, 총자산, 자본금, 자본총계, 매출액, 영업이익, 당기순이익
                year = cols[0].text.strip()[:4]  # YYYY-MM-DD에서 YYYY만 추출
                sales = cols[4].text.strip().replace(',', '')  # 매출액
                profit = cols[5].text.strip().replace(',', '')  # 영업이익
                
                try:
                    result[f'매출액_{year}'] = int(sales)
                    result[f'영업이익_{year}'] = int(profit)
                    logger.info(f"{year}년도 데이터 추출 완료: 매출액={sales}, 영업이익={profit}")
                except ValueError as e:
                    logger.error(f"숫자 변환 중 오류 발생: {str(e)}")
                    continue
        
        # 회사명 정보만 있어도 반환
        if len(result) > 0:
            result['검색완료'] = 'Y'  # 검색은 완료됨
            return result
            
        return None
        
    except Exception as e:
        logger.error(f"매출현황 데이터 추출 중 오류 발생: {str(e)}")
        return None
