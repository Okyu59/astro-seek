from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from playwright.async_api import async_playwright # [변경] Async API 사용
import os
import traceback
import urllib.parse
import asyncio

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
    return {
        "summary": f"⚠️ 데이터 조회 실패\n원인: {error_msg}\n\n(예비 데이터를 표시합니다.)",
        "planets": [
            {"name": "Sun", "sign": "Virgo", "house": "10 House"},
            {"name": "Moon", "sign": "Leo", "house": "9 House"},
            {"name": "Mercury", "sign": "Libra", "house": "11 House"},
            {"name": "Venus", "sign": "Scorpio", "house": "12 House"},
            {"name": "Mars", "sign": "Virgo", "house": "10 House"},
            {"name": "Jupiter", "sign": "Sagittarius", "house": "1 House"}
        ]
    }

# --- [Async Scraping Logic] ---
async def scrape_astro_seek(birth_date, birth_time, city):
    print(f"[Scraper] Async job started for {birth_date} {birth_time}")
    
    try:
        year, month, day = birth_date.split('-')
        hour, minute = birth_time.split(':')
    except Exception as e:
        return get_fallback_data(birth_date, f"Date Parsing Error: {str(e)}")

    data = {"planets": [], "summary": ""}
    
    # URL 직접 구성
    base_url = "https://horoscopes.astro-seek.com/calculate-birth-chart-horoscope-online/"
    params = {
        "narozeni_den": int(day),
        "narozeni_mesic": int(month),
        "narozeni_rok": year,
        "narozeni_hodina": hour,
        "narozeni_minuta": minute,
        "narozeni_city": "Seoul, South Korea",
        "narozeni_mesto_hidden": "Seoul",
        "narozeni_stat_hidden": "KR",
        "narozeni_podstat_kratky_hidden": "",
        "narozeni_podstat_hidden": "Seoul"
    }
    
    target_url = f"{base_url}?{urllib.parse.urlencode(params)}"
    print(f"[Scraper] Target: {target_url}")

    # 브라우저 옵션
    launch_args = [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--single-process',
        '--disable-extensions',
        '--disable-images' 
    ]
    
    # [변경] Async Context Manager 사용
    async with async_playwright() as p:
        browser = None
        try:
            # [변경] await 사용
            browser = await p.chromium.launch(headless=True, args=launch_args)
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                viewport={"width": 800, "height": 600}
            )
            page = await context.new_page()
            
            print("[Scraper] Navigating...")
            # [변경] await 사용
            await page.goto(target_url, timeout=60000, wait_until="domcontentloaded")
            
            print("[Scraper] Waiting for table...")
            try:
                await page.wait_for_selector('.horoscope_table', timeout=20000)
            except:
                title = await page.title()
                print(f"[Error] Table not found. Page title: {title}")
                raise Exception("Result table not found (Timeout)")
            
            print("[Scraper] Extracting data...")
            rows = await page.query_selector_all(".horoscope_table tr")
            
            for row in rows:
                # [변경] inner_text()도 await 필요
                text = await row.inner_text()
                
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
            print(f"[Scraper] Error: {str(e)}")
            traceback.print_exc()
            return get_fallback_data(birth_date, str(e))
        
        finally:
            if browser:
                await browser.close()

# --- [API Endpoints] ---

@app.post("/api/chart")
async def get_chart(request: ChartRequest):
    # [변경] await 사용하여 비동기 함수 호출
    result = await scrape_astro_seek(request.date, request.time, request.city)
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


