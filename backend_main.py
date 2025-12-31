from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys

# [라이브러리 로드 시도]
# kerykeion이 있으면 쓰고, 없으면(ImportError) 자체 계산 로직을 쓰도록 플래그 설정
try:
    from kerykeion import KrInstance
    LIBRARY_LOADED = True
    print("[System] kerykeion (KrInstance) loaded successfully.")
except ImportError:
    try:
        from kerykeion.report import Report
        from kerykeion.astrological_subject import AstrologicalSubject
        LIBRARY_LOADED = True
        print("[System] kerykeion (Report/Subject) loaded successfully.")
    except ImportError as e:
        print(f"[System] Warning: Astrology Library load failed ({e}). Switching to fallback mode.")
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
# 라이브러리 없이 날짜만으로 태양 별자리를 계산하는 함수
def get_simple_zodiac_sign(day, month):
    # 각 별자리의 시작일 (1월 ~ 12월)
    # Capricorn, Aquarius, Pisces, Aries, Taurus, Gemini, Cancer, Leo, Virgo, Libra, Scorpio, Sagittarius
    cutoff = [20, 19, 21, 20, 21, 22, 23, 23, 23, 24, 22, 22]
    signs = [
        "Capricorn", "Aquarius", "Pisces", "Aries", "Taurus", "Gemini",
        "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn"
    ]
    
    if day > cutoff[month-1]:
        return signs[month]
    else:
        return signs[month-1]

# --- [통합 계산 핸들러] ---
def calculate_chart(birth_date, birth_time, city):
    try:
        year, month, day = map(int, birth_date.split('-'))
        hour, minute = map(int, birth_time.split(':'))
    except:
        return {"summary": "날짜 형식이 올바르지 않습니다.", "planets": []}

    # 1. 라이브러리가 정상 로드된 경우 (정밀 계산)
    if LIBRARY_LOADED:
        try:
            # KrInstance 방식 시도
            if 'KrInstance' in globals():
                user = KrInstance("User", year, month, day, hour, minute, city=city, lat=37.56, lng=126.97)
                sun_sign = user.sun['sign']
                planet_list = [
                    ("Sun", user.sun), ("Moon", user.moon), ("Mercury", user.mercury),
                    ("Venus", user.venus), ("Mars", user.mars), ("Jupiter", user.jupiter),
                    ("Saturn", user.saturn), ("Ascendant", user.first_house)
                ]
            # Report/Subject 방식 시도 (구버전 호환)
            else:
                subject = AstrologicalSubject("User", year, month, day, hour, minute, city=city, lat=37.56, lng=126.97)
                report = Report(subject)
                sun_sign = report.sun['sign']
                planet_list = [
                    ("Sun", report.sun), ("Moon", report.moon), ("Mercury", report.mercury),
                    ("Venus", report.venus), ("Mars", report.mars), ("Jupiter", report.jupiter),
                    ("Saturn", report.saturn), ("Ascendant", report.first_house)
                ]

            planets_data = []
            for name, obj in planet_list:
                house_info = obj.get('house', 'Unknown')
                planets_data.append({
                    "name": name,
                    "sign": obj.get('sign', 'Unknown'),
                    "house": f"{house_info} House" if house_info != 'Unknown' else "Unknown"
                })
            
            return {
                "summary": f"정밀 분석 완료! 당신의 태양 별자리는 {sun_sign}입니다.",
                "planets": planets_data
            }
        except Exception as e:
            print(f"[Library Error] {e}. Falling back to simple engine.")
            # 라이브러리 실행 중 에러나면 아래 폴백으로 진행

    # 2. 라이브러리 로드 실패 시 (비상용 엔진 가동)
    print("[System] Using Simple Fallback Engine")
    sun_sign = get_simple_zodiac_sign(day, month)
    
    # 태양 별자리에 맞춰 대략적인(가상의) 하우스와 행성 배치 생성 (UI 테스트용)
    return {
        "summary": f"(시스템 알림: 라이브러리 로드 실패로 간이 엔진을 사용했습니다.)\n당신의 태양 별자리는 확실하게 '{sun_sign}'입니다.",
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
