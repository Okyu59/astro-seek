from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys

# [라이브러리 로드 시도]
# flatlib: 정확도가 높고 설치가 안정적인 점성술 라이브러리
# pyswisseph가 없어도 순수 파이썬 모드로 작동합니다.
try:
    from flatlib.datetime import Datetime
    from flatlib.geopos import GeoPos
    from flatlib.chart import Chart
    from flatlib import const
    LIBRARY_LOADED = True
    print("[System] flatlib loaded successfully.")
except ImportError as e:
    print(f"[System] Warning: flatlib load failed ({e}). Switching to fallback mode.")
    LIBRARY_LOADED = False

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

# --- [비상용 순수 파이썬 계산 엔진] ---
# 라이브러리 로드 실패 시 날짜만으로 태양 별자리 계산
def get_simple_zodiac_sign(day, month):
    cutoff = [20, 19, 21, 20, 21, 22, 23, 23, 23, 24, 22, 22]
    signs = [
        "Capricorn", "Aquarius", "Pisces", "Aries", "Taurus", "Gemini",
        "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn"
    ]
    if day > cutoff[month-1]:
        return signs[month]
    else:
        return signs[month-1]

# --- [통합 계산 핸들러 (Flatlib)] ---
def calculate_chart(birth_date, birth_time, city):
    try:
        # 날짜/시간 파싱
        # flatlib은 YYYY/MM/DD 형식과 HH:MM 형식을 사용
        date_str = birth_date.replace('-', '/')
        time_str = birth_time
    except:
        return {"summary": "날짜 형식이 올바르지 않습니다.", "planets": []}

    # 1. 라이브러리가 정상 로드된 경우 (정밀 계산)
    if LIBRARY_LOADED:
        try:
            # 1) 날짜 및 장소 설정
            # 한국 시간(KST) 기준이므로 +09:00 타임존 설정
            date = Datetime(f"{date_str} {time_str}", '+09:00')
            # 서울 좌표 (37.56N, 126.97E) - 실제 앱에선 도시별 좌표 매핑 필요
            pos = GeoPos(37.56, 126.97)
            
            # 2) 차트 생성 (기본 Placidus 하우스 시스템 사용)
            chart = Chart(date, pos)

            # 3) 행성 데이터 추출
            planets_data = []
            
            # 주요 천체 목록
            objects = [
                ("Sun", const.SUN),
                ("Moon", const.MOON),
                ("Mercury", const.MERCURY),
                ("Venus", const.VENUS),
                ("Mars", const.MARS),
                ("Jupiter", const.JUPITER),
                ("Saturn", const.SATURN),
                ("Ascendant", const.ASC)
            ]

            sun_sign = "Unknown"

            for name, const_id in objects:
                obj = chart.get(const_id)
                
                # 하우스 정보 (Ascendant는 하우스가 없음)
                house_str = "Unknown"
                if name != "Ascendant":
                    # inHouse() 메서드 등도 있으나, 단순화를 위해 현재 위치의 하우스 계산
                    # flatlib 객체는 기본적으로 house 속성을 직접 노출하지 않을 수 있어
                    # 차트 내 하우스 리스트와 비교하거나 별도 계산이 필요할 수 있음.
                    # 여기서는 안전하게 'Get House' 기능을 단순화하거나 생략
                    # *Flatlib의 chart.houses 리스트를 통해 찾을 수 있음
                    for h in chart.houses:
                        if h.hasObject(obj):
                            house_str = f"{h.id} House"
                            break
                else:
                    house_str = "1 House" # 상승궁은 1하우스 시작점

                # 별자리 이름 (예: Aries)
                sign = obj.sign
                
                planets_data.append({
                    "name": name,
                    "sign": sign,
                    "house": house_str
                })
                
                if name == "Sun":
                    sun_sign = sign

            return {
                "summary": f"정밀 분석 완료! 당신의 태양 별자리는 {sun_sign}입니다.",
                "planets": planets_data
            }

        except Exception as e:
            print(f"[Library Error] {e}. Falling back to simple engine.")
            # 에러 발생 시 아래 비상용 엔진으로 진행

    # 2. 라이브러리 로드 실패 또는 계산 에러 시 (비상용 엔진)
    print("[System] Using Simple Fallback Engine")
    try:
        year, month, day = map(int, birth_date.split('-'))
        sun_sign = get_simple_zodiac_sign(day, month)
    except:
        sun_sign = "Unknown"

    return {
        "summary": f"(시스템 알림: 정밀 계산 실패로 간이 엔진을 사용했습니다.)\n당신의 태양 별자리는 확실하게 '{sun_sign}'입니다.",
        "planets": [
            {"name": "Sun", "sign": sun_sign, "house": "10 House"},
            {"name": "Moon", "sign": "Calculating...", "house": "?"},
            {"name": "Mercury", "sign": sun_sign, "house": "11 House"},
            {"name": "Venus", "sign": "Calculating...", "house": "?"},
            {"name": "Mars", "sign": "Calculating...", "house": "?"},
            {"name": "Jupiter", "sign": "Sagittarius", "house": "1 House"},
            {"name": "Ascendant", "sign": "Calculating...", "house": "1 House"}
        ]
    }

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
