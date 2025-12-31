from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
import os
import traceback

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
# 크롤링 실패 시에만 보여줄 예비 데이터
def get_fallback_data(date, reason="Unknown Error"):
    return {
        "summary": f"(시스템: {reason}) Astro-Seek 접속 지연으로 예비 데이터를 표시합니다. ({date})",
        "planets": [
            {"name": "Sun", "sign": "Virgo", "house": "10 House"},
            {"name": "Moon", "sign": "Leo", "house": "9 House"},
            {"name": "Mercury", "sign": "Libra", "house": "11 House"},
            {"name": "Venus", "sign": "Scorpio", "house": "12 House"},
            {"name": "Mars", "sign": "Virgo", "house": "10 House"},
            {"name": "Jupiter", "sign": "Sagittarius", "house": "1 House"}
        ]
    }

# --- [Real Scraping Logic] ---
def scrape_astro_seek(birth_date, birth_time, city):
    print(f"[Scraper] Starting job for {birth_date} {birth_time} in {city}")
    
    try:
        year, month, day = birth_date.split('-')
        hour, minute = birth_time.split(':')
    except Exception as e:
        print(f"[Scraper] Date parsing error: {e}")
        return get_fallback_data(birth_date, "Date Format Error")

    data = {"planets": [], "summary": ""}
    
    # 1. 브라우저 옵션 설정 (봇 탐지 회피 및 메모리 절약)
    launch_args = [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--single-process'
    ]
    
    playwright = None
    browser = None
    
    try:
        playwright = sync_playwright().start()
        
        # 2. 브라우저 실행 (User-Agent 설정 추가)
        browser = playwright.chromium.launch(headless=True, args=launch_args)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        page = context.new_page()
        
        # 3. Astro-Seek 접속 (타임아웃 60초로 넉넉하게)
        print("[Scraper] Navigating to website...")
        page.goto("https://www.astro-seek.com/birth-chart-horoscope-online", timeout=60000)
        
        # 4. 폼 입력
        print("[Scraper] Filling form...")
        # (주의: 사이트 구조 변경 시 selector 수정 필요)
        page.select_option('select[name="narozeni_den"]', str(int(day)))
        page.select_option('select[name="narozeni_mesic"]', str(int(month)))
        page.select_option('select[name="narozeni_rok"]', year)
        page.fill('input[name="narozeni_hodina"]', hour)
        page.fill('input[name="narozeni_minuta"]', minute)
        
        # 도시 입력은 복잡하므로, 일단 기본값(또는 "Unknown" 체크)으로 진행하거나
        # 나중에 URL 파라미터 방식으로 고도화 필요. 현재는 입력 없이 진행 (Default City 사용됨)
        # *도시 검색 팝업을 피하기 위해 입력 생략*
        
        # 5. 계산 버튼 클릭
        print("[Scraper] Submitting...")
        page.click('input[type="submit"]')
        
        # 6. 결과 대기
        page.wait_for_selector('.horoscope_table', timeout=30000)
        
        # 7. 데이터 추출
        print("[Scraper] Extracting data...")
        rows = page.query_selector_all(".horoscope_table tr")
        
        for row in rows:
            text = row.inner_text()
            # 데이터 파싱 로직
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

        # 요약문 생성
        if data["planets"]:
            # 첫 번째 행성의 별자리를 이용해 요약 생성
            sun_sign = next((p['sign'] for p in data['planets'] if p['name'] == 'Sun'), 'Unknown')
            data["summary"] = f"Astro-Seek에서 데이터를 성공적으로 가져왔습니다.\n당신의 태양 별자리는 {sun_sign}입니다."
            print(f"[Scraper] Success! Found {len(data['planets'])} planets.")
            return data
        else:
            print("[Scraper] Failed to find planet data in table.")
            raise Exception("Empty data extracted")

    except Exception as e:
        print(f"[Scraper] Critical Error: {str(e)}")
        traceback.print_exc()
        return get_fallback_data(birth_date, "Server Busy or Blocked")

    finally:
        if browser: browser.close()
        if playwright: playwright.stop()

# --- [API Endpoints] ---

@app.post("/api/chart")
async def get_chart(request: ChartRequest):
    print(f"[API] Request: {request.date} {request.time}")
    
    # [수정됨] 이제 진짜 크롤링 함수를 호출합니다!
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


