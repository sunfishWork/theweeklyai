import feedparser
import requests
import json
from datetime import datetime
from bs4 import BeautifulSoup
import ollama

# RSS 피드 URL
RSS_URL = "https://spectrum.ieee.org/rss"


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
        # 광고 이미지 필터링
        if "ad" not in img_url.lower() and "advertisement" not in img_url.lower() and "banner" not in img_url.lower():
            return img_url
    return ""


def generate_summary_and_translations(text, title):
    """Ollama를 사용해 영문 요약, 한글 제목, 한글 요약 생성"""
    # 영문 요약 생성 프롬프트
    summary_prompt = f"Summarize the following text in 2-3 sentences in English:\n\n{text}"
    summary_response = ollama.chat(
        model="llama3.2:3b",
        messages=[{"role": "user", "content": summary_prompt}]
    )
    english_summary = summary_response["message"]["content"].strip()

    # 한글 제목 생성 프롬프트
    title_translation_prompt = f"Translate the following English title into Korean:\n\n{title}"
    title_response = ollama.chat(
        model="llama3.2:3b",
        messages=[{"role": "user", "content": title_translation_prompt}]
    )
    korean_title = title_response["message"]["content"].strip()

    # 한글 요약 생성 프롬프트
    summary_translation_prompt = f"Translate the following English summary into Korean:\n\n{english_summary}"
    summary_translation_response = ollama.chat(
        model="llama3.2:3b",
        messages=[{"role": "user", "content": summary_translation_prompt}]
    )
    korean_summary = summary_translation_response["message"]["content"].strip()

    return english_summary, korean_title, korean_summary


def process_rss_feed():
    """RSS 피드를 처리하고 요약, 번역, 이미지 URL 생성"""
    # RSS 피드 파싱
    feed = feedparser.parse(RSS_URL)
    results = []

    for entry in feed.entries[:5]:  # 최신 5개 항목만 처리
        title = entry.get("title", "")
        link = entry.get("link", "")
        description = entry.get("description", "")
        published = entry.get("published", "")

        # 대표 이미지 추출
        image = extract_image(description)

        # 텍스트 콘텐츠 정제
        clean_description = clean_html_content(description)

        # 요약 및 번역 생성
        try:
            english_summary, korean_title, korean_summary = generate_summary_and_translations(clean_description, title)
        except Exception as e:
            print(f"Error processing entry '{title}': {e}")
            continue

        # 결과 데이터 구조
        result = {
            "link": link,
            "image": image,
            "published": published,
            "title": title,  # 영문 제목
            "summary": english_summary,
            "korean_title": korean_title,
            "korean_summary": korean_summary
        }
        results.append(result)

    return results


def save_to_json(data, filename="summaries.json"):
    """결과를 JSON 파일로 저장"""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    try:
        # RSS 피드 처리
        results = process_rss_feed()

        # JSON 파일로 저장
        save_to_json(results)
        print(f"Successfully saved summaries to summaries.json")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()