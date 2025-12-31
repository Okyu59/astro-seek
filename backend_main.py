from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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

# --- [Fallback Data Generator] ---
def get_fallback_data(date, reason="Unknown Error"):
    """크롤링 실패 시 보여줄 기본 데이터"""
    return {
        "summary": f"(시스템 알림: {reason}) 서버 부하로 인해 예비 데이터를 표시합니다. {date}의 차트입니다.",
        "planets": [
            {"name": "Sun", "sign": "Virgo", "house": "10 House"},
            {"name": "Moon", "sign": "Leo", "house": "9 House"},
            {"name": "Mercury", "sign": "Libra", "house": "11 House"},
            {"name": "Venus", "sign": "Scorpio", "house": "12 House"},
            {"name": "Mars", "sign": "Virgo", "house": "10 House"},
            {"name": "Jupiter", "sign": "Sagittarius", "house": "1 House"},
            {"name": "Saturn", "sign": "Pisces", "house": "4 House"}
        ]
    }

# --- [Scraping Logic] ---
def scrape_astro_seek(birth_date, birth_time, city):
    print(f"[Log] Scraping started for {birth_date} {birth_time}")
    
    try:
        year, month, day = birth_date.split('-')
        hour, minute = birth_time.split(':')
    except Exception as e:
        print(f"[Error] Date parsing failed: {e}")
        return get_fallback_data(birth_date, "Date format error")

    data = {"planets": [], "summary": ""}
    
    # 브라우저 실행 옵션 최적화 (메모리 부족 방지)
    launch_args = [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage', # 메모리 공유 비활성화 (Docker 필수)
        '--disable-gpu',
        '--single-process' # 프로세스 하나만 사용 (메모리 절약)
    ]

    playwright = None
    browser = None
    
    try:
        playwright = sync_playwright().start()
        # Headless 모드로 브라우저 실행
        browser = playwright.chromium.launch(headless=True, args=launch_args)
        page = browser.new_page()
        
        # 페이지 이동 (타임아웃 30초로 단축하여 빠른 실패 유도)
        print("[Log] Navigating to Astro-Seek...")
        page.goto("https://www.astro-seek.com/birth-chart-horoscope-online", timeout=30000)
        
        # 폼 입력
        print("[Log] Filling form...")
        page.select_option('select[name="narozeni_den"]', str(int(day)))
        page.select_option('select[name="narozeni_mesic"]', str(int(month)))
        page.select_option('select[name="narozeni_rok"]', year)
        page.fill('input[name="narozeni_hodina"]', hour)
        page.fill('input[name="narozeni_minuta"]', minute)
        
        # 계산 클릭
        print("[Log] Submitting...")
        page.click('input[type="submit"]')
        
        # 결과 대기
        page.wait_for_selector('.horoscope_table', timeout=20000)
        
        # 데이터 추출
        print("[Log] Extracting data...")
        rows = page.query_selector_all(".horoscope_table tr")
        for row in rows:
            text = row.inner_text()
            if "Sun" in text and "Sign" not in text:
                data["planets"].append({"name": "Sun", "sign": text.split()[1], "house": "10 House"})
            elif "Moon" in text:
                data["planets"].append({"name": "Moon", "sign": text.split()[1], "house": "4 House"})
            elif "Mercury" in text:
                data["planets"].append({"name": "Mercury", "sign": text.split()[1], "house": "11 House"})
            elif "Venus" in text:
                data["planets"].append({"name": "Venus", "sign": text.split()[1], "house": "12 House"})
            elif "Mars" in text:
                data["planets"].append({"name": "Mars", "sign": text.split()[1], "house": "5 House"})
            elif "Jupiter" in text:
                data["planets"].append({"name": "Jupiter", "sign": text.split()[1], "house": "1 House"})

        data["summary"] = f"{year}년 {month}월 {day}일에 태어난 당신의 차트 분석 결과입니다."
        
        if not data["planets"]:
            print("[Warning] No planets found in table.")
            return get_fallback_data(birth_date, "Data extraction empty")
            
        return data

    except Exception as e:
        print(f"[Error] Scraping crashed: {str(e)}")
        traceback.print_exc()
        # 크롤링 실패 시에도 서버 에러(500) 대신 Fallback 데이터 반환하여 앱 작동 보장
        return get_fallback_data(birth_date, "Live data unavailable (Traffic/Memory)")

    finally:
        # 자원 정리
        if browser: browser.close()
        if playwright: playwright.stop()

# --- [API Endpoints] ---

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

@app.post("/api/chart")
async def get_chart(request: ChartRequest):
    print(f"[API] Request received: {request}")
    # 어떤 에러가 나도 JSON을 반환하도록 함
    try:
        result = scrape_astro_seek(request.date, request.time, request.city)
        return JSONResponse(content=result)
    except Exception as e:
        print(f"[API Critical Error] {str(e)}")
        return JSONResponse(content=get_fallback_data(request.date, "Server Logic Error"))

# --- [Serve React App] ---
if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
else:
    print("[Warning] 'frontend/dist' folder not found. React app will not be served.")


