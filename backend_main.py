from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys

# [라이브러리 로드]
try:
    from flatlib.datetime import Datetime
    from flatlib.geopos import GeoPos
    from flatlib.chart import Chart
    from flatlib import const
    LIBRARY_LOADED = True
except ImportError as e:
    LIBRARY_LOADED = False
    IMPORT_ERROR = str(e)

app = FastAPI()

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

def calculate_chart(birth_date, birth_time, city):
    # 1. 라이브러리 자체가 안 깔린 경우
    if not LIBRARY_LOADED:
        return {
            "summary": f"⚠️ 서버 설정 오류: 라이브러리 로드 실패\n({IMPORT_ERROR})\nrequirements.txt에 flatlib이 있는지 확인해주세요.",
            "planets": []
        }

    try:
        # 날짜 포맷 변환 (YYYY-MM-DD -> YYYY/MM/DD)
        date_str = birth_date.replace('-', '/')
        # 시간 포맷 (HH:MM) - 초 단위가 없으면 :00 추가
        time_str = birth_time if len(birth_time.split(':')) == 3 else f"{birth_time}:00"
        
        # 1) 시간 객체 생성 (+09:00 한국 표준시 고정)
        # 에러 포인트 1: 날짜/시간 형식이 안 맞으면 여기서 터짐
        date = Datetime(f"{date_str} {time_str}", '+09:00')
        
        # 2) 위치 객체 생성 (서울)
        pos = GeoPos(37.56, 126.97)
        
        # 3) 차트 계산
        # 에러 포인트 2: 하우스 시스템 계산 중 에러 가능성
        chart = Chart(date, pos, IDs=const.LIST_OBJECTS)

        planets_data = []
        objects = [
            ("Sun", const.SUN), ("Moon", const.MOON), ("Mercury", const.MERCURY),
            ("Venus", const.VENUS), ("Mars", const.MARS), ("Jupiter", const.JUPITER),
            ("Saturn", const.SATURN), ("Ascendant", const.ASC)
        ]

        sun_sign = "Unknown"

        for name, const_id in objects:
            try:
                obj = chart.get(const_id)
                sign = obj.sign
                
                # 하우스 계산 (안전하게 처리)
                house_str = "Unknown"
                if name != "Ascendant":
                    # 단순하게 하우스 리스트 순회
                    for h in chart.houses:
                        if h.hasObject(obj):
                            house_str = f"{h.id} House"
                            break
                else:
                    house_str = "1 House"

                planets_data.append({
                    "name": name, 
                    "sign": sign, 
                    "house": house_str
                })
                
                if name == "Sun": sun_sign = sign
            except:
                continue

        return {
            "summary": f"분석 성공! 당신의 태양 별자리는 {sun_sign}입니다.",
            "planets": planets_data
        }

    except Exception as e:
        # [핵심] 에러가 발생하면 구체적인 영어 메시지를 반환함
        return {
            "summary": f"⚠️ 계산 실패 원인: {str(e)}\n(이 메시지를 알려주세요)",
            "planets": [
                {"name": "Error", "sign": "Check", "house": "Logs"}
            ]
        }

@app.post("/api/chart")
async def get_chart(request: ChartRequest):
    result = calculate_chart(request.date, request.time, request.city)
    return JSONResponse(content=result)

# --- Frontend Serving ---
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
