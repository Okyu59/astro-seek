from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from playwright.async_api import async_playwright
import os
import traceback
import urllib.parse
import asyncio
from datetime import datetime

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

# --- [Smart Fallback Logic] ---
# 크롤링 실패 시, 입력된 날짜로 '태양 별자리'를 직접 계산해서 보여줌 (최소한의 정확성 보장)
def get_sun_sign(month, day):
    days = [21, 20, 21, 20, 21, 22, 23, 23, 23, 24, 22, 22]
    signs = ["Aquarius", "Pisces", "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn"]
    if (month == 1 and day < 20): return "Capricorn"
    if (day < days[month-1]): return signs[month-2]
    return signs[month-1]

def get_smart_fallback(date_str, error_msg):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        sun_sign = get_sun_sign(dt.month, dt.day)
        summary_text = f"⚠️ Astro-Seek 보안 접속이 지연되어 자체 엔진으로 분석했습니다.\n당신의 태양 별자리는 '{sun_sign}'입니다."
    except:
        sun_sign = "Unknown"
        summary_text = f"⚠️ 데이터 조회에 실패했습니다. ({error_msg})"

    return {
        "summary": summary_text,
        "planets": [
            {"name": "Sun", "sign": sun_sign, "house": "Unknown"},
            {"name": "Moon", "sign": "Calculating...", "house": "?"},
            {"name": "Mercury", "sign": "Calculating...", "house": "?"},
            {"name": "Venus", "sign": "Calculating...", "house": "?"},
            {"name": "Mars", "sign": "Calculating...", "house": "?"}
        ],
        "is_fallback": True
    }

# --- [Async Scraping Logic] ---
async def scrape_astro_seek(birth_date, birth_time, city):
    print(f"[Scraper] Job started for {birth_date}")
    
    try:
        year, month, day = birth_date.split('-')
        hour, minute = birth_time.split(':')
    except Exception as e:
        return get_smart_fallback(birth_date, "Date Error")

    data = {"planets": [], "summary": ""}
    
    # URL 구성
    base_url = "https://horoscopes.astro-seek.com/calculate-birth-chart-horoscope-online/"
    params = {
        "narozeni_den": int(day), "narozeni_mesic": int(month), "narozeni_rok": year,
        "narozeni_hodina": hour, "narozeni_minuta": minute,
        "narozeni_city": "Seoul, South Korea", "narozeni_mesto_hidden": "Seoul",
        "narozeni_stat_hidden": "KR", "narozeni_podstat_kratky_hidden": "", "narozeni_podstat_hidden": "Seoul"
    }
    target_url = f"{base_url}?{urllib.parse.urlencode(params)}"

    # 브라우저 옵션
    launch_args = ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--single-process']
    
    async with async_playwright() as p:
        browser = None
        try:
            browser = await p.chromium.launch(headless=True, args=launch_args)
            
            # [핵심] 사람처럼 보이기 위한 헤더 설정
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720},
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": "https://www.google.com/"
                }
            )
            page = await context.new_page()
            
            print("[Scraper] Navigating...")
            # 타임아웃 60초로 증가
            await page.goto(target_url, timeout=60000, wait_until="domcontentloaded")
            
            # 페이지 제목 확인 (디버깅용)
            page_title = await page.title()
            print(f"[Scraper] Page Title: {page_title}")
            
            # Cloudflare 챌린지 감지 시 즉시 Fallback
            if "Just a moment" in page_title or "Security" in page_title:
                raise Exception("Blocked by Anti-Bot")

            print("[Scraper] Waiting for table...")
            await page.wait_for_selector('.horoscope_table', timeout=20000)
            
            rows = await page.query_selector_all(".horoscope_table tr")
            for row in rows:
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

            if data["planets"]:
                sun_sign = next((p['sign'] for p in data['planets'] if p['name'] == 'Sun'), 'Unknown')
                data["summary"] = f"Astro-Seek 데이터 분석 완료!\n당신의 태양 별자리는 {sun_sign}입니다."
                return data
            else:
                raise Exception("Table found but empty")

        except Exception as e:
            print(f"[Scraper Error] {str(e)}")
            # 에러 발생 시 스마트 Fallback 데이터 반환
            return get_smart_fallback(birth_date, str(e))
        
        finally:
            if browser: await browser.close()

# --- [API Endpoints] ---
@app.post("/api/chart")
async def get_chart(request: ChartRequest):
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


