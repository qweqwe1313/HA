from flask import Flask, request, jsonify
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import datetime
import requests

app = Flask(__name__)

@app.route('/')
def index():
    return "✅ 서버 정상 작동 중!"

# ✅ 날짜 필터링된 URL 생성
def build_filtered_url(keyword):
    today = datetime.date.today()
    one_month_ago = today - datetime.timedelta(days=30)
    date_param = f"&sm=tab_opt&date_from={one_month_ago.strftime('%Y%m%d')}&date_to={today.strftime('%Y%m%d')}"
    return f"https://search.naver.com/search.naver?query={keyword}{date_param}"

# ✅ 자동완성 키워드
def get_autocomplete_keywords(base_keyword):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = f"https://ac.search.naver.com/nx/ac?q={base_keyword}&st=111&r_format=json"
        res = requests.get(url, headers=headers)
        data = res.json()
        return [item[0] for item in data.get('items', [])[0]]
    except:
        return []

# ✅ 관련 검색어
def get_related_keywords(driver, keyword):
    driver.get(f"https://search.naver.com/search.naver?query={keyword}")
    time.sleep(2)
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, "div.related_srch a")
        return [el.text for el in elements if el.text.strip()]
    except:
        return []

# ✅ DOM 추천 키워드
def get_dom_based_keywords(driver):
    time.sleep(2)
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, "a[data-template-type='alsoSearch']")
        return [el.text.strip() for el in elements if el.text.strip()]
    except:
        return []

# ✅ 슬라이드 키워드
def get_slider_keywords(driver):
    keywords = set()
    click_count = 0
    max_clicks = 10
    try:
        while click_count < max_clicks:
            time.sleep(1.5)
            elements = driver.find_elements(By.CSS_SELECTOR, "div[data-template-type='alsoSearch'] a")
            for el in elements:
                text = el.text.strip()
                if text:
                    keywords.add(text)
            try:
                next_btn = driver.find_element(By.CSS_SELECTOR, "div.flicking-arrow-next")
                if "disabled" in next_btn.get_attribute("class"):
                    break
                next_btn.click()
                click_count += 1
            except:
                break
    except:
        pass
    return list(keywords)

# ✅ 블로그 제목 수집
def crawl_titles(driver, keyword, scroll_count=5, max_titles=10):
    url = build_filtered_url(keyword)
    driver.get(url)
    time.sleep(2)

    try:
        blog_tab = driver.find_element(By.CSS_SELECTOR, "a[href*='tab.blog.all']")
        blog_tab.click()
        time.sleep(2)
    except:
        return []

    for _ in range(scroll_count):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

    try:
        elements = driver.find_elements(By.CSS_SELECTOR, "a.title_link")
        return [f"[{keyword}] {el.text.strip()}" for el in elements if el.text.strip()]
    except:
        return []

# ✅ 추천 키워드 클릭 후 블로그 수집
def collect_from_popular_topics(driver, base_keyword, max_titles=10):
    driver.get(f"https://search.naver.com/search.naver?query={base_keyword}")
    time.sleep(2)
    titles = []

    try:
        topic_links = driver.find_elements(By.CSS_SELECTOR, "a.fds-comps-keyword-chip, a.fds-modules-keyword-chip")
        for i in range(len(topic_links)):
            topic_links = driver.find_elements(By.CSS_SELECTOR, "a.fds-comps-keyword-chip, a.fds-modules-keyword-chip")
            if i >= len(topic_links):
                break

            keyword_text = topic_links[i].text.strip()
            if not keyword_text:
                continue

            try:
                topic_links[i].click()
                time.sleep(2)

                try:
                    blog_tab = driver.find_element(By.CSS_SELECTOR, "a[href*='tab.blog.all']")
                    blog_tab.click()
                    time.sleep(2)
                except:
                    driver.back()
                    time.sleep(2)
                    continue

                post_elements = driver.find_elements(By.CSS_SELECTOR, "a.title_link")
                post_titles = [f"[{keyword_text}] {el.text.strip()}" for el in post_elements if el.text.strip()]
                titles.extend(post_titles[:max_titles])

                driver.back()
                time.sleep(1.5)
                driver.back()
                time.sleep(1.5)

            except:
                driver.get(f"https://search.naver.com/search.naver?query={base_keyword}")
                time.sleep(2)

    except:
        pass

    return titles

# ✅ 전체 키워드 수집
def get_all_keywords(driver, base_keyword):
    related = get_related_keywords(driver, base_keyword)
    auto = get_autocomplete_keywords(base_keyword)
    dom = get_dom_based_keywords(driver)
    slider = get_slider_keywords(driver)
    all_kw = list(set([base_keyword] + related + auto + dom + slider))
    return all_kw

# ✅ 크롤러 실행
def run_keyword_collector_full(base_keyword):
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = uc.Chrome(options=options)

    try:
        all_titles = []

        popular_titles = collect_from_popular_topics(driver, base_keyword, max_titles=10)
        all_titles.extend(popular_titles)

        all_keywords = get_all_keywords(driver, base_keyword)
        for kw in all_keywords:
            titles = crawl_titles(driver, kw, scroll_count=5, max_titles=10)
            all_titles.extend(titles)

        return all_titles

    finally:
        driver.quit()

# ✅ 실행 API
@app.route("/run", methods=["POST"])
def run_scraper():
    data = request.get_json()
    keyword = data.get("keyword")

    if not keyword:
        return jsonify({"error": "No keyword provided"}), 400

    result = run_keyword_collector_full(keyword)
    return jsonify({
        "keyword": keyword,
        "results": result,
        "count": len(result)
    })

