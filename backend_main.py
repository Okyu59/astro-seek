from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

# [수정] kerykeion의 메인 클래스인 KrInstance를 사용하도록 변경 (ImportError 해결)
# KrInstance는 계산과 리포트를 통합한 헬퍼 클래스입니다.
try:
    from kerykeion import KrInstance
except ImportError:
    try:
        from kerykeion.kr_instance import KrInstance
    except ImportError:
        print("Warning: Failed to import kerykeion.KrInstance")
        KrInstance = None

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
    if KrInstance is None:
        return {"summary": "서버 구성 오류: 점성술 라이브러리를 로드할 수 없습니다.", "planets": []}

    try:
        year, month, day = map(int, birth_date.split('-'))
        hour, minute = map(int, birth_time.split(':'))
        
        # [수정] KrInstance 사용: 서울 좌표 기준 계산 (필요시 geonames API 연동 가능)
        user = KrInstance(
            "User", year, month, day, hour, minute, 
            city=city, lat=37.56, lng=126.97, tz_str="Asia/Seoul"
        )
        
        planets_data = []
        # KrInstance 객체는 행성 정보를 속성(Dictionary)으로 직접 가집니다.
        planet_list = [
            ("Sun", user.sun), ("Moon", user.moon), 
            ("Mercury", user.mercury), ("Venus", user.venus), 
            ("Mars", user.mars), ("Jupiter", user.jupiter), 
            ("Saturn", user.saturn), ("Ascendant", user.first_house)
        ]

        for name, obj in planet_list:
            house_info = obj.get('house', 'Unknown')
            planets_data.append({
                "name": name,
                "sign": obj['sign'],
                "house": f"{house_info} House" if house_info != 'Unknown' else "Unknown"
            })

        return {
            "summary": f"자체 엔진 분석 완료! 당신의 태양 별자리는 {user.sun['sign']}입니다.",
            "planets": planets_data
        }

    except Exception as e:
        print(f"Error: {e}")
        return {"summary": "계산 오류가 발생했습니다.", "planets": []}

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
