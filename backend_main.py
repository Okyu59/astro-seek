from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
# import kerykeion  <-- 불필요한 import 제거
# [수정] 라이브러리 내부 경로에서 직접 클래스를 가져오도록 변경 (ImportError 해결)
try:
    from kerykeion import Report, AstrologicalSubject
except ImportError:
    from kerykeion.report import Report
    from kerykeion.astrological_subject import AstrologicalSubject

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

# --- [자체 계산 엔진] ---
def calculate_chart(birth_date, birth_time, city):
    try:
        year, month, day = map(int, birth_date.split('-'))
        hour, minute = map(int, birth_time.split(':'))
        
        # 서울 좌표 기준 계산 (필요시 geonames API 연동 가능)
        subject = AstrologicalSubject(
            "User", year, month, day, hour, minute, 
            city=city, lat=37.56, lng=126.97, tz_str="Asia/Seoul"
        )
        report = Report(subject)
        
        planets_data = []
        planet_list = [
            ("Sun", report.sun), ("Moon", report.moon), 
            ("Mercury", report.mercury), ("Venus", report.venus), 
            ("Mars", report.mars), ("Jupiter", report.jupiter), 
            ("Saturn", report.saturn), ("Ascendant", report.first_house)
        ]

        for name, obj in planet_list:
            house_info = obj.get('house', 'Unknown')
            planets_data.append({
                "name": name,
                "sign": obj['sign'],
                "house": f"{house_info} House" if house_info != 'Unknown' else "Unknown"
            })

        return {
            "summary": f"자체 엔진 분석 완료! 당신의 태양 별자리는 {report.sun['sign']}입니다.",
            "planets": planets_data
        }

    except Exception as e:
        print(f"Error: {e}")
        return {"summary": "계산 오류", "planets": []}

# --- [API] ---
@app.post("/api/chart")
async def get_chart(request: ChartRequest):
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
