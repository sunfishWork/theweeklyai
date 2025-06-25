import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
from urllib.parse import urljoin
import re


# robots.txt 확인 함수
def check_robots_txt(url):
    robots_url = urljoin(url, "/robots.txt")
    try:
        response = requests.get(robots_url, timeout=5)
        if response.status_code == 200:
            if "Disallow: /discover/blog/" in response.text:
                print("robots.txt에 의해 /discover/blog/ 크롤링이 금지되어 있습니다.")
                return False
        return True
    except requests.RequestException as e:
        print(f"robots.txt 확인 중 오류: {e}")
        return True  # robots.txt 접근 실패 시 기본적으로 크롤링 허용 가정


# 날짜 형식을 파싱하는 함수
def parse_date(date_str):
    try:
        # 예상되는 날짜 형식: "YYYY-MM-DD" 또는 "Month DD, YYYY"
        date_str = date_str.strip()
        if re.match(r"\d{4}-\d{2}-\d{2}", date_str):
            return datetime.strptime(date_str, "%Y-%m-%d")
        else:
            return datetime.strptime(date_str, "%B %d, %Y")
    except ValueError:
        print(f"날짜 파싱 실패: {date_str}")
        return None


# 블로그 페이지 크롤링 함수
def crawl_deepmind_blog(start_date, end_date):
    base_url = "https://deepmind.google/discover/blog/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    # robots.txt 확인
    # if not check_robots_txt(base_url):
    #     return []

    updated_pages = []
    visited_urls = set()
    urls_to_visit = [base_url]

    while urls_to_visit:
        current_url = urls_to_visit.pop(0)
        if current_url in visited_urls:
            continue

        visited_urls.add(current_url)
        try:
            response = requests.get(current_url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # 블로그 게시물 목록에서 링크와 날짜 추출
            for article in soup.find_all("article"):
                # 링크 추출
                link_tag = article.find("a", href=True)
                if not link_tag:
                    continue
                article_url = urljoin(base_url, link_tag["href"])

                # 날짜 추출 (메타데이터 또는 특정 태그에서)
                date_tag = article.find("time") or article.find("span", class_=re.compile("date|published"))
                if not date_tag:
                    continue

                date_str = date_tag.get_text(strip=True) or date_tag.get("datetime")
                if not date_str:
                    continue

                article_date = parse_date(date_str)
                if not article_date:
                    continue

                # 날짜 범위 확인
                if start_date <= article_date <= end_date:
                    updated_pages.append({
                        "url": article_url,
                        "title": link_tag.get_text(strip=True),
                        "date": article_date.strftime("%Y-%m-%d")
                    })

                # 하위 링크 수집 (페이지네이션 또는 관련 링크)
                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    if "/discover/blog/" in href and href not in visited_urls:
                        full_url = urljoin(base_url, href)
                        if full_url not in urls_to_visit:
                            urls_to_visit.append(full_url)

            # 요청 간 딜레이 추가
            time.sleep(1)

        except requests.RequestException as e:
            print(f"페이지 크롤링 중 오류: {current_url}, 오류: {e}")
            continue

    return updated_pages


# 메인 실행
if __name__ == "__main__":
    # 지난 주 월요일(2025-06-16) ~ 일요일(2025-06-22)
    start_date = datetime(2025, 6, 16)
    end_date = datetime(2025, 6, 22)

    print(f"{start_date.strftime('%Y-%m-%d')}부터 {end_date.strftime('%Y-%m-%d')}까지 업데이트된 페이지 크롤링 중...")
    updated_pages = crawl_deepmind_blog(start_date, end_date)

    # 결과 출력
    if updated_pages:
        print("\n업데이트된 페이지:")
        for page in updated_pages:
            print(f"- 제목: {page['title']}")
            print(f"  URL: {page['url']}")
            print(f"  날짜: {page['date']}")
    else:
        print("지정된 기간 내 업데이트된 페이지를 찾지 못했습니다.")