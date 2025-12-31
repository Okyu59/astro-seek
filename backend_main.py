from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import kerykeion # 점성술 계산 라이브러리
from kerykeion import Report, AstrologicalSubject

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

# --- [Core: Astrology Calculation Engine] ---
def calculate_chart(birth_date, birth_time, city):
    try:
        year, month, day = map(int, birth_date.split('-'))
        hour, minute = map(int, birth_time.split(':'))
        
        # Kerykeion 라이브러리를 사용해 차트 생성 (Astro-Seek와 동일한 방식)
        # 도시 좌표는 편의상 서울(Seoul)로 고정하거나, geonames 등을 연동할 수 있음
        # 여기서는 단순화를 위해 서울 좌표(37.5665, 126.9780) 사용
        subject = AstrologicalSubject(
            "User", 
            year, month, day, 
            hour, minute, 
            city=city, 
            lat=37.56, lng=126.97, # 실제 서비스에선 도시별 좌표 매핑 필요
            tz_str="Asia/Seoul"
        )
        report = Report(subject)
        
        # 데이터 포맷팅
        planets_data = []
        
        # 주요 행성 추출
        # Kerykeion은 행성 이름을 영어로 반환함
        planet_list = [
            ("Sun", report.sun), 
            ("Moon", report.moon), 
            ("Mercury", report.mercury), 
            ("Venus", report.venus), 
            ("Mars", report.mars), 
            ("Jupiter", report.jupiter), 
            ("Saturn", report.saturn),
            ("Ascendant", report.first_house) # 상승궁(1하우스 커스프)
        ]

        for name, obj in planet_list:
            # sign(별자리) 정보 추출
            sign_name = obj['sign']
            house_num = obj.get('house', 'Unknown') # 하우스 정보가 없을 수도 있음
            
            planets_data.append({
                "name": name,
                "sign": sign_name,
                "house": f"{house_num} House" if house_num != 'Unknown' else "Unknown"
            })

        return {
            "summary": f"자체 엔진으로 분석된 정밀 차트입니다.\n당신의 태양 별자리는 {report.sun['sign']}입니다.",
            "planets": planets_data
        }

    except Exception as e:
        print(f"Calculation Error: {e}")
        return {
            "summary": "계산 중 오류가 발생했습니다.",
            "planets": []
        }

# --- [API Endpoints] ---

@app.post("/api/chart")
async def get_chart(request: ChartRequest):
    # 크롤링(scrape_astro_seek) 대신 계산 함수(calculate_chart) 호출
    result = calculate_chart(request.date, request.time, request.city)
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
