from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys

# [수정] 라이브러리 로드 방식 개선 (세부 모듈 직접 임포트)
# KrInstance 대신 Core 클래스인 Report와 AstrologicalSubject를 직접 가져옵니다.
try:
    from kerykeion.report import Report
    from kerykeion.astrological_subject import AstrologicalSubject
    LIBRARY_LOADED = True
    print("[System] kerykeion modules loaded successfully.")
except ImportError as e:
    print(f"[System] Primary Import Failed: {e}")
    try:
        # 폴백: 패키지 루트에서 시도
        from kerykeion import Report, AstrologicalSubject
        LIBRARY_LOADED = True
        print("[System] kerykeion loaded from root package.")
    except ImportError as e2:
        print(f"[System] Critical Error: Failed to load Astrology Library. {e2}")
        LIBRARY_LOADED = False
        Report = None
        AstrologicalSubject = None

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
    # 라이브러리 로드 실패 시 안전장치
    if not LIBRARY_LOADED:
        return {
            "summary": "서버 구성 오류: 점성술 라이브러리(kerykeion)를 로드할 수 없습니다. 배포 로그를 확인해주세요.", 
            "planets": []
        }

    try:
        year, month, day = map(int, birth_date.split('-'))
        hour, minute = map(int, birth_time.split(':'))
        
        # [수정] AstrologicalSubject와 Report 클래스 직접 사용
        # 서울 좌표 기준 계산 (필요시 geonames API 연동 가능)
        subject = AstrologicalSubject(
            "User", year, month, day, hour, minute, 
            city=city, lat=37.56, lng=126.97, tz_str="Asia/Seoul"
        )
        report = Report(subject)
        
        planets_data = []
        # Report 객체는 행성 정보를 딕셔너리로 반환합니다.
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
                "sign": obj.get('sign', 'Unknown'),
                "house": f"{house_info}" if house_info != 'Unknown' else "Unknown"
            })

        sun_sign = report.sun.get('sign', 'Unknown')
        return {
            "summary": f"자체 엔진 분석 완료! 당신의 태양 별자리는 {sun_sign}입니다.",
            "planets": planets_data
        }

    except Exception as e:
        print(f"[Calculation Error] {e}")
        return {"summary": f"계산 중 오류가 발생했습니다: {str(e)}", "planets": []}

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
