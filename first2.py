import feedparser
import requests
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import ollama
from dateutil.parser import parse as parse_date

# RSS 피드 URL 리스트
RSS_URLS = [
    # Arxiv

    # IEEE Spectrum
    "https://spectrum.ieee.org/customfeeds/feed/all-topics/rss",

    # MIT Tech review
    # "https://www.technologyreview.com/feed/", # 최신만

    # Meta ai

    # Nvidia ai
    "https://feeds.feedburner.com/nvidiablog",

    # Google ai
    "https://blog.google/technology/ai/rss/",

    # Ms ai

    # Visualcapitalist
    "https://feeds.feedburner.com/visualcapitalist",    # 일주일 정도

    # Venturebeat
    "https://feeds.feedburner.com/venturebeat/SZYF",    # 일주일 정도

    # At&t news

    # Telus newsroom

    # Bain & Company

    # Boston consulting group

    # NEW
    "https://feeds.arstechnica.com/arstechnica/technology-lab", #한달 정도 피드 제공
    "https://www.wired.com/feed/tag/ai/latest/rss", # 2주 정도 피드 제공
    "https://www.mckinsey.com/insights/rss", # 2주 정도 피드 제공
    "https://www.lightreading.com/rss.xml", # 2주 정도 피드 제공
    "https://cloudblog.withgoogle.com/rss/", # 10일 정도

    # "https://techcrunch.com/feed/", # 최신 피드만 제공
    # "https://www.theverge.com/rss/index.xml",   # 최신 피드만 제공
    # "https://www.rcrwireless.com/feed", #최신 피드만 제공


]


def clean_html_content(html_content):
    """HTML 콘텐츠에서 텍스트만 추출"""
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(strip=True)


def extract_image(html_content):
    """HTML 콘텐츠에서 대표 이미지 URL 추출"""
    soup = BeautifulSoup(html_content, "html.parser")
    img_tag = soup.find("img")
    if img_tag and img_tag.get("src"):
        img_url = img_tag["src"]
        return img_url
    return ""


def generate_summary_and_translations(text, title):
    """Ollama를 사용해 영문 요약, 한글 제목, 한글 요약 생성"""
    # 영문 요약 생성 프롬프트
    summary_prompt = f"""
    Summarize the following text in 4 paragraphs, each approximately 80 words, in English. 
    Additionally, include two separate paragraphs analyzing the impact on the AI industry and the Telecommunication industry, each approximately 80 words.
    Subtitle "Impact on the AI industry: " and "Impact on the Telecommunication industry: " must included.
    Start the response directly. 
    Structure the response as follows:

    First paragraph:
    Second paragraph:
    Third paragraph:
    Fourth paragraph:
    Impact on the AI industry:
    Impact on the Telecommunication industry:

    {text}"""
    summary_response = ollama.chat(
        model="llama3.2:3b",
        messages=[{"role": "user", "content": summary_prompt}]
    )
    english_summary = summary_response["message"]["content"].strip()

    # 한글 제목 생성 프롬프트
    title_translation_prompt = f"""
    Translate the following English title into Korean:
    Start the response directly. 
    \n\n{title}"""
    title_response = ollama.chat(
        model="llama3.2:3b",
        messages=[{"role": "user", "content": title_translation_prompt}]
    )
    korean_title = title_response["message"]["content"].strip()

    # 한글 요약 생성 프롬프트
    summary_translation_prompt = f"""
    Translate the following English summary into Korean:
    Start the response directly.
    \n\n{english_summary}"""
    summary_translation_response = ollama.chat(
        model="llama3.2:3b",
        messages=[{"role": "user", "content": summary_translation_prompt}]
    )
    korean_summary = summary_translation_response["message"]["content"].strip()

    return english_summary, korean_title, korean_summary


def fetch_webpage_content(url):
    """웹페이지 콘텐츠를 가져옴"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching webpage {url}: {e}")
        return ""


def process_rss_feed(rss_url):
    """단일 RSS 피드를 처리하고 요약, 번역, 이미지 URL 생성"""
    # RSS 피드 파싱
    feed = feedparser.parse(rss_url)
    results = []

    # 오늘 날짜 기준으로 지난 주 월요일부터 일요일까지의 날짜 범위 계산
    today = datetime.now()
    days_to_last_monday = today.weekday() + 7
    last_monday = today - timedelta(days=days_to_last_monday)
    last_sunday = last_monday + timedelta(days=6)
    print(f"Processing RSS: {rss_url}")
    print(f"Last Monday: {last_monday}")
    print(f"Last Sunday: {last_sunday}")

    for entry in feed.entries:
        title = entry.get("title", "")
        link = entry.get("link", "")
        published = entry.get("published", entry.get("pubDate", ""))

        # published 날짜를 파싱
        try:
            published_date = parse_date(published)
            published_date = published_date.replace(tzinfo=None)  # 시간대 정보 제거
            print(f"Published date: {published_date}")
        except (ValueError, TypeError):
            print(f"Skipping entry '{title}' due to invalid date format")
            continue

        # 지난 주 월요일부터 일요일까지의 콘텐츠만 처리
        if last_monday.date() <= published_date.date() <= last_sunday.date():
            # 웹페이지 콘텐츠 가져오기
            webpage_content = fetch_webpage_content(link)
            if not webpage_content:
                print(f"Skipping entry '{title}' due to failed webpage fetch")
                continue

            # 대표 이미지 추출
            image = extract_image(webpage_content)

            # 텍스트 콘텐츠 정제
            clean_description = clean_html_content(webpage_content)
            print(f"cleaned description: {clean_description}")
            if not clean_description:
                print(f"Skipping entry '{title}' due to empty content")
                continue

            debug = False
            if not debug:
                # 요약 및 번역 생성
                try:
                    english_summary, korean_title, korean_summary = generate_summary_and_translations(clean_description, title)
                except Exception as e:
                    print(f"Error processing entry '{title}': {e}")
                    continue

                # 결과 데이터 구조
                result = {
                    "rss_source": rss_url,
                    "link": link,
                    "image": image,
                    "published": published,
                    "eng_title": title,
                    "eng_summary": english_summary,
                    "title": korean_title,
                    "summary": korean_summary
                }
                results.append(result)

    return results


def process_multiple_rss_feeds(rss_urls):
    """여러 RSS 피드를 처리"""
    all_results = []
    for rss_url in rss_urls:
        try:
            results = process_rss_feed(rss_url)
            all_results.extend(results)
        except Exception as e:
            print(f"Error processing RSS feed {rss_url}: {e}")
    return all_results


def save_to_json(data, filename="summaries.json"):
    """결과를 JSON 파일로 저장"""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    try:
        # 여러 RSS 피드 처리
        results = process_multiple_rss_feeds(RSS_URLS)

        # JSON 파일로 저장
        save_to_json(results)
        print(f"Successfully saved summaries to summaries.json")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()