# SMINFO 크롤러 CSS 선택자 목록

**최종 업데이트:** 2023-10-27 (예시)

이 문서는 `sminfo_crawler` 프로젝트에서 사용되는 주요 CSS 선택자들을 관리합니다.

## 1. `login.py` (로그인 관련 선택자)

- **로그인 페이지 이동 버튼 (메인 페이지 상단)**
    - 선택자: `'#wrap > div.header.clearfix > div.global_box > ul > li:nth-child(2) > a'`
    - 사용처: `login.py`, `LoginManager.login()`
    - 페이지 컨텍스트: SMINFO 메인 페이지
- **아이디(ID) 입력 필드**
    - 선택자: `'#id'`
    - 사용처: `login.py`, `LoginManager.login()`
    - 페이지 컨텍스트: SMINFO 로그인 페이지
- **비밀번호(Password) 입력 필드**
    - 선택자: `'#pwd'`
    - 사용처: `login.py`, `LoginManager.login()`
    - 페이지 컨텍스트: SMINFO 로그인 페이지
- **로그인 실행 버튼 (로그인 폼 내부)**
    - 선택자: `'#contents_sub > div:nth-child(3) > div > div.login_lr_box.clearfix > div.lr_text_r > div:nth-child(1) > form > button > span'`
    - 사용처: `login.py`, `LoginManager.login()`
    - 페이지 컨텍스트: SMINFO 로그인 페이지
- **로그아웃 버튼 (로그인 후 상태 확인용)**
    - 선택자: `'#main_link > div > div.main_login_box.m_main_login_box > div > form > fieldset > div > button > span'`
    - 사용처: `login.py`, `LoginManager.check_login_status()`, `LoginManager.logout()`
    - 페이지 컨텍스트: SMINFO 메인 페이지 (로그인 후)

## 2. `scraper.py` (검색 및 정보 추출 관련 선택자)

- **회사명 검색 입력 필드**
    - 선택자: `'#searchTxt'`
    - 사용처: `scraper.py`, `search_company_name()`
    - 페이지 컨텍스트: (예상) 기업 검색이 가능한 페이지 (예: 메인 페이지 또는 기업 검색 전용 페이지)
- **검색 실행 버튼**
    - 선택자: `'#searchBtn'`
    - 사용처: `scraper.py`, `search_company_name()`
    - 페이지 컨텍스트: (예상) 기업 검색이 가능한 페이지
- **검색 결과 테이블 (기본 정보 추출 시)**
    - 선택자: `'table.table_list'`
    - 사용처: `scraper.py`, `extract_company_info()`
    - 페이지 컨텍스트: 기업 검색 결과 목록 페이지
    - **하위 요소 선택자**:
        - 회사명: `'tr:first-child td:nth-child(2)'` (테이블 내 상대 경로)
        - 대표자명: `'tr:first-child td:nth-child(3)'` (테이블 내 상대 경로)
        - 사업자등록번호: `'tr:first-child td:nth-child(4)'` (테이블 내 상대 경로)
        - 주소: `'tr:first-child td:nth-child(5)'` (테이블 내 상대 경로)
- **매출현황 테이블 (매출/이익 정보 추출 시)**
    - 선택자: `'table.list_table.type02'` (이 클래스를 가진 테이블 중 `<caption>`이 '매출현황'인 것을 찾습니다)
    - 사용처: `scraper.py`, `extract_sales_profit()`
    - 페이지 컨텍스트: 기업 정보 상세 페이지 또는 매출현황 정보가 표시되는 섹션
- **검색된 회사명 표시 제목 (매출/이익 정보 추출 시)**
    - 선택자: `'#contents_sub > div:nth-child(3) > div > h4.table_title'`
    - 사용처: `scraper.py`, `extract_sales_profit()`
    - 페이지 컨텍스트: 기업 정보 상세 페이지 또는 매출현황 정보가 표시되는 섹션

## 3. 참고: 초기 분석 단계에서 고려되었던 선택자 (현재 코드 미사용)

- `'table.list_table.type02 tbody td.alignL > a'`
    - 설명: `requests` + `BeautifulSoup` 접근 방식 시, `상세검색.html` 파일의 검색 결과 목록에서 각 기업명을 가리키는 `<a>` 태그를 선택하기 위한 것이었음.
    - 현재 `scraper.py`의 `extract_sales_profit` 함수에서도 `table.list_table.type02` 클래스를 가진 테이블을 참조하지만, 이는 "매출현황" 테이블을 대상으로 함. 