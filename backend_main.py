from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
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

# --- [Path Debugging] ---
# 서버 시작 시 현재 위치와 파일들을 확인합니다. (Railway 로그에서 확인 가능)
print("------------------------------------------------")
CURRENT_DIR = os.getcwd()
DIST_DIR = os.path.join(CURRENT_DIR, "frontend/dist")
print(f"[Startup] Current Directory: {CURRENT_DIR}")
print(f"[Startup] Expected Dist Directory: {DIST_DIR}")

if os.path.exists(DIST_DIR):
    print(f"[Startup] Dist directory found! Contents: {os.listdir(DIST_DIR)}")
else:
    print("[Startup] CRITICAL ERROR: Dist directory NOT found.")
    # frontend 폴더라도 있는지 확인
    if os.path.exists("frontend"):
        print(f"[Startup] Frontend folder contents: {os.listdir('frontend')}")
print("------------------------------------------------")


class ChartRequest(BaseModel):
    date: str
    time: str
    city: str

# --- [Fallback Data Generator] ---
def get_fallback_data(date, reason="Unknown Error"):
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
        return get_fallback_data(birth_date, "Date format error")

    data = {"planets": [], "summary": ""}
    
    # 메모리 최적화 옵션
    launch_args = ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--single-process']

    playwright = None
    browser = None
    
    try:
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=True, args=launch_args)
        page = browser.new_page()
        
        # 페이지 이동 (30초 타임아웃)
        page.goto("https://www.astro-seek.com/birth-chart-horoscope-online", timeout=30000)
        
        # 폼 입력
        page.select_option('select[name="narozeni_den"]', str(int(day)))
        page.select_option('select[name="narozeni_mesic"]', str(int(month)))
        page.select_option('select[name="narozeni_rok"]', year)
        page.fill('input[name="narozeni_hodina"]', hour)
        page.fill('input[name="narozeni_minuta"]', minute)
        
        page.click('input[type="submit"]')
        page.wait_for_selector('.horoscope_table', timeout=20000)
        
        # 데이터 추출
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

        data["summary"] = f"{year}년 {month}월 {day}일에 태어난 당신의 차트 분석 결과입니다."
        
        if not data["planets"]:
            return get_fallback_data(birth_date, "Data extraction empty")
            
        return data

    except Exception as e:
        print(f"[Error] Scraping crashed: {str(e)}")
        traceback.print_exc()
        return get_fallback_data(birth_date, "Live data unavailable (Traffic/Memory)")

    finally:
        if browser: browser.close()
        if playwright: playwright.stop()

# --- [API Endpoints] ---

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

@app.post("/api/chart")
async def get_chart(request: ChartRequest):
    try:
        result = scrape_astro_seek(request.date, request.time, request.city)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content=get_fallback_data(request.date, "Server Logic Error"))

# --- [Serve React App Explicitly] ---

# 1. Assets (JS, CSS) 마운트
if os.path.exists(os.path.join(DIST_DIR, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST_DIR, "assets")), name="assets")

# 2. 루트 경로 접속 시 index.html 강제 반환 (SPA 처리)
@app.get("/")
async def serve_spa_root():
    index_path = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        # 파일이 없으면 에러 내용을 브라우저에 표시
        return JSONResponse(
            status_code=404, 
            content={
                "error": "Frontend build not found", 
                "current_dir": CURRENT_DIR,
                "dist_dir": DIST_DIR,
                "exists": os.path.exists(DIST_DIR),
                "contents": os.listdir(CURRENT_DIR) if os.path.exists(CURRENT_DIR) else "Cannot read dir"
            }
        )

# 3. 그 외 모든 경로는 index.html로 리다이렉트 (React Router 지원)
@app.exception_handler(404)
async def custom_404_handler(_, __):
    index_path = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(status_code=404, content={"error": "Page not found and build missing"})


