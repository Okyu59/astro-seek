from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
from datetime import datetime, timedelta

# [라이브러리 로드]
# Swiss Ephemeris (pyswisseph): 점성술 업계 표준 정밀 계산 라이브러리
# Astro-Seek, Astro.com 등에서 사용하는 엔진과 동일한 기반입니다.
try:
    import swisseph as swe
    LIBRARY_LOADED = True
    # Ephemeris 파일 경로 설정 (없으면 기본 내장 Moshier 모델 사용 - 약 3000년 범위 내 정밀)
    # swe.set_ephe_path('/usr/share/ephe') 
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

def get_zodiac_sign(longitude):
    """황경(0~360도)을 별자리 이름으로 변환"""
    signs = [
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ]
    index = int(longitude / 30)
    return signs[index % 12]

def calculate_chart(birth_date, birth_time, city):
    # 1. 라이브러리가 안 깔린 경우
    if not LIBRARY_LOADED:
        return {
            "summary": f"⚠️ 서버 설정 오류: pyswisseph 로드 실패\n({IMPORT_ERROR})\nrequirements.txt에 pyswisseph가 있는지 확인해주세요.",
            "planets": []
        }

    try:
        # 날짜/시간 파싱
        year, month, day = map(int, birth_date.split('-'))
        hour, minute = map(int, birth_time.split(':'))
        
        # 1. 시간 변환 (KST -> UTC)
        # 한국 표준시(KST)는 UTC+9입니다. 정확한 계산을 위해 UTC로 변환합니다.
        dt_kst = datetime(year, month, day, hour, minute)
        dt_utc = dt_kst - timedelta(hours=9)
        
        # 율리우스 적일(Julian Day) 계산을 위한 십진수 시간(Decimal Hour)
        hour_decimal = dt_utc.hour + (dt_utc.minute / 60.0) + (dt_utc.second / 3600.0)
        
        # 2. 율리우스 적일(Julian Day) 계산
        jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour_decimal)
        
        # 3. 위치 설정 (서울: 37.56N, 126.97E)
        # 실제 서비스에서는 입력된 City에 따라 좌표를 찾아야 합니다.
        lat = 37.56
        lon = 126.97
        
        # 4. 하우스 계산 (Placidus 시스템: b'P')
        # cusps: 하우스 커스프(경계), ascmc: [ASC, MC, ARMC, Vertex, ...]
        cusps, ascmc = swe.houses(jd, lat, lon, b'P')
        
        # 상승궁 (Ascendant)
        asc_sign = get_zodiac_sign(ascmc[0])
        
        # 5. 행성 위치 계산
        planets_data = []
        
        # 행성 ID 매핑
        bodies = [
            ("Sun", swe.SUN),
            ("Moon", swe.MOON),
            ("Mercury", swe.MERCURY),
            ("Venus", swe.VENUS),
            ("Mars", swe.MARS),
            ("Jupiter", swe.JUPITER),
            ("Saturn", swe.SATURN)
        ]
        
        sun_sign = "Unknown"

        for name, body_id in bodies:
            # 행성 위치 계산 (UT 기준)
            # 반환값: ((long, lat, dist, ...), flags)
            res = swe.calc_ut(jd, body_id)
            longitude = res[0][0]
            
            # 별자리 판별
            sign = get_zodiac_sign(longitude)
            
            # 하우스 판별
            # swe.house_pos: 행성의 황경과 위도를 이용해 하우스 위치(1.0 ~ 12.99)를 계산
            try:
                h_pos = swe.house_pos(jd, lat, lon, b'P', longitude, 0.0)
                house_num = int(h_pos)
                planet_house = f"{house_num} House"
            except:
                planet_house = "Unknown"

            planets_data.append({
                "name": name,
                "sign": sign,
                "house": planet_house
            })
            
            if name == "Sun":
                sun_sign = sign

        # 상승궁 추가
        planets_data.append({
            "name": "Ascendant",
            "sign": asc_sign,
            "house": "1 House"
        })

        return {
            "summary": f"정밀 분석(Swiss Ephemeris) 완료! 당신의 태양 별자리는 {sun_sign}입니다.",
            "planets": planets_data
        }
        
    except Exception as e:
        return {
            "summary": f"⚠️ 계산 실패 원인: {str(e)}",
            "planets": []
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
