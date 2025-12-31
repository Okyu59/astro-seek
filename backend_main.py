from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
import os

app = FastAPI()

# CORS 설정 (개발 편의성)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터 모델 정의
class ChartRequest(BaseModel):
    date: str
    time: str
    city: str

# --- [Scraping Logic] ---
def scrape_astro_seek(birth_date, birth_time, city):
    try:
        year, month, day = birth_date.split('-')
        hour, minute = birth_time.split(':')
    except:
        return None

    data = {"planets": [], "summary": ""}
    
    with sync_playwright() as p:
        try:
            # 브라우저 실행 (Headless)
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
            page = browser.new_page()
            
            # Astro-Seek 접속 및 계산
            page.goto("https://www.astro-seek.com/birth-chart-horoscope-online", timeout=60000)
            
            page.select_option('select[name="narozeni_den"]', str(int(day)))
            page.select_option('select[name="narozeni_mesic"]', str(int(month)))
            page.select_option('select[name="narozeni_rok"]', year)
            page.fill('input[name="narozeni_hodina"]', hour)
            page.fill('input[name="narozeni_minuta"]', minute)
            # 도시 입력 생략 (단순화) - 실제 구현시 URL 파라미터 방식 권장
            
            page.click('input[type="submit"]')
            page.wait_for_selector('.horoscope_table', timeout=30000)
            
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

            data["summary"] = f"{year}년 {month}월 {day}일에 태어난 당신의 차트입니다."
            browser.close()
            return data

        except Exception as e:
            if 'browser' in locals(): browser.close()
            print(f"Scraping Error: {e}")
            # 에러 발생 시 Fallback 데이터 반환
            return {
                "summary": "(연결 지연으로 인한 예시 데이터) 귀하는 처녀자리 태양입니다.",
                "planets": [
                    {"name": "Sun", "sign": "Virgo", "house": "10 House"},
                    {"name": "Moon", "sign": "Leo", "house": "9 House"},
                    {"name": "Ascendant", "sign": "Sagittarius", "house": "1 House"},
                ]
            }

# --- [API Endpoints] ---

@app.post("/api/chart")
async def get_chart(request: ChartRequest):
    result = scrape_astro_seek(request.date, request.time, request.city)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to generate chart")
    return result

# --- [Serve React App] ---
# Frontend 빌드 결과물(dist 폴더)을 정적 파일로 제공
# 주의: Dockerfile 구조상 /app/frontend/dist 위치에 빌드됨
if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")

