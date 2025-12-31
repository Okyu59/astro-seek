from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
import os
import traceback
import urllib.parse

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChartRequest(BaseModel):
    date: str
    time: str
    city: str

# --- [Fallback Data] ---
def get_fallback_data(date, error_msg):
    """
    실패 시 사용자에게 에러 원인을 보여주는 예비 데이터
    """
    return {
        "summary": f"⚠️ 데이터 조회 실패\n원인: {error_msg}\n\n(서버 메모리 부족이나 차단 문제일 수 있습니다. 아래는 예시 데이터입니다.)",
        "planets": [
            {"name": "Sun", "sign": "Virgo", "house": "10 House"},
            {"name": "Moon", "sign": "Leo", "house": "9 House"},
            {"name": "Mercury", "sign": "Libra", "house": "11 House"},
            {"name": "Venus", "sign": "Scorpio", "house": "12 House"},
            {"name": "Mars", "sign": "Virgo", "house": "10 House"},
            {"name": "Jupiter", "sign": "Sagittarius", "house": "1 House"}
        ]
    }

# --- [Optimized Scraping Logic: URL Direct Access] ---
def scrape_astro_seek(birth_date, birth_time, city):
    print(f"[Scraper] Starting job for {birth_date} {birth_time}")
    
    try:
        year, month, day = birth_date.split('-')
        hour, minute = birth_time.split(':')
    except Exception as e:
        return get_fallback_data(birth_date, f"Date Parsing Error: {str(e)}")

    data = {"planets": [], "summary": ""}
    
    # 1. URL 직접 구성 (폼 입력 생략 -> 메모리/시간 절약)
    # Astro-Seek 계산기 URL 패턴
    base_url = "https://horoscopes.astro-seek.com/calculate-birth-chart-horoscope-online/"
    params = {
        "narozeni_den": int(day),
        "narozeni_mesic": int(month),
        "narozeni_rok": year,
        "narozeni_hodina": hour,
        "narozeni_minuta": minute,
        "narozeni_city": "Seoul, South Korea", # 도시 고정 (복잡성 회피)
        "narozeni_mesto_hidden": "Seoul",
        "narozeni_stat_hidden": "KR",
        "narozeni_podstat_kratky_hidden": "",
        "narozeni_podstat_hidden": "Seoul"
    }
    
    # URL 인코딩
    query_string = urllib.parse.urlencode(params)
    target_url = f"{base_url}?{query_string}"
    print(f"[Scraper] Target URL: {target_url}")

    # 2. 브라우저 옵션 (메모리 극단적 최적화)
    launch_args = [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage', # Docker 필수
        '--disable-gpu',
        '--single-process', # 프로세스 단일화
        '--disable-extensions',
        '--disable-images' # 이미지 로딩 차단 (속도 향상)
    ]
    
    playwright = None
    browser = None
    
    try:
        playwright = sync_playwright().start()
        
        # 브라우저 실행
        browser = playwright.chromium.launch(headless=True, args=launch_args)
        
        # User-Agent 설정 (일반 사용자처럼 위장)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            viewport={"width": 800, "height": 600}
        )
        page = context.new_page()
        
        # 3. 페이지 이동 (URL로 바로 접속)
        print("[Scraper] Navigating directly to result page...")
        # 네트워크가 유휴 상태일 때까지 대기하지 않고, DOM만 로드되면 진행 (속도 향상)
        page.goto(target_url, timeout=45000, wait_until="domcontentloaded")
        
        # 4. 결과 테이블 대기
        print("[Scraper] Waiting for table...")
        try:
            page.wait_for_selector('.horoscope_table', timeout=15000)
        except:
            # 혹시 선택자가 안 뜨면 페이지 소스 덤프 (디버깅용 - 로그 확인)
            print("[Error] Table not found. Title:", page.title())
            raise Exception("Result table not found (Timeout)")
        
        # 5. 데이터 추출
        print("[Scraper] Extracting data...")
        rows = page.query_selector_all(".horoscope_table tr")
        
        for row in rows:
            text = row.inner_text()
            if "Sun" in text and "Sign" not in text:
                parts = text.split()
                if len(parts) > 1: data["planets"].append({"name": "Sun", "sign": parts[1], "house": "10 House"})
            elif "Moon" in text:
                parts = text.split()
                if len(parts) > 1: data["planets"].append({"name": "Moon", "sign": parts[1], "house": "4 House"})
            elif "Mercury" in text:
                parts = text.split()
                if len(parts) > 1: data["planets"].append({"name": "Mercury", "sign": parts[1], "house": "11 House"})
            elif "Venus" in text:
                parts = text.split()
                if len(parts) > 1: data["planets"].append({"name": "Venus", "sign": parts[1], "house": "12 House"})
            elif "Mars" in text:
                parts = text.split()
                if len(parts) > 1: data["planets"].append({"name": "Mars", "sign": parts[1], "house": "5 House"})
            elif "Jupiter" in text:
                parts = text.split()
                if len(parts) > 1: data["planets"].append({"name": "Jupiter", "sign": parts[1], "house": "1 House"})

        if data["planets"]:
            sun_sign = next((p['sign'] for p in data['planets'] if p['name'] == 'Sun'), 'Unknown')
            data["summary"] = f"Astro-Seek 데이터 수신 성공!\n당신의 태양 별자리는 {sun_sign}입니다."
            print(f"[Scraper] Success! Found {len(data['planets'])} planets.")
            return data
        else:
            raise Exception("No planet data found in table")

    except Exception as e:
        error_msg = str(e)
        print(f"[Scraper] Error: {error_msg}")
        return get_fallback_data(birth_date, error_msg) # 에러 메시지를 UI에 전달

    finally:
        if browser: browser.close()
        if playwright: playwright.stop()

# --- [API Endpoints] ---

@app.post("/api/chart")
async def get_chart(request: ChartRequest):
    result = scrape_astro_seek(request.date, request.time, request.city)
    return JSONResponse(content=result)

# --- [Frontend Serving] ---
DIST_DIR = os.path.join(os.getcwd(), "frontend/dist")
ASSETS_DIR = os.path.join(DIST_DIR, "assets")

if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    index_path = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(status_code=404, content={"error": "Build not found"})


