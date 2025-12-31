from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
from datetime import datetime, timedelta
from google import genai # 최신 라이브러리

# [라이브러리 로드]
try:
    import swisseph as swe
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

# [설정] Gemini API 클라이언트
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = None

if GEMINI_API_KEY:
    try:
        # 공백 제거 후 클라이언트 초기화
        client = genai.Client(api_key=GEMINI_API_KEY.strip())
        print(f"[System] Gemini API Client Configured. (Key Length: {len(GEMINI_API_KEY.strip())})")
    except Exception as e:
        print(f"[System] Gemini Client Initialization Error: {e}")
else:
    print("[System] Warning: GEMINI_API_KEY environment variable not found.")

# --- [데이터 모델] ---
class ChartRequest(BaseModel):
    date: str
    time: str
    city: str

class PlanetData(BaseModel):
    name: str
    sign: str
    house: str

class AskRequest(BaseModel):
    question: str
    planets: list[PlanetData]

def get_zodiac_sign(longitude):
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    index = int(longitude / 30)
    return signs[index % 12]

def calculate_chart(birth_date, birth_time, city):
    if not LIBRARY_LOADED:
        return {"summary": f"⚠️ 라이브러리 에러: {IMPORT_ERROR}", "planets": []}

    try:
        year, month, day = map(int, birth_date.split('-'))
        hour, minute = map(int, birth_time.split(':'))
        
        dt_kst = datetime(year, month, day, hour, minute)
        dt_utc = dt_kst - timedelta(hours=9)
        hour_decimal = dt_utc.hour + (dt_utc.minute / 60.0) + (dt_utc.second / 3600.0)
        
        jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour_decimal)
        lat, lon = 37.56, 126.97
        
        cusps, ascmc = swe.houses(jd, lat, lon, b'P')
        asc_sign = get_zodiac_sign(ascmc[0])
        
        planets_data = []
        bodies = [("Sun", swe.SUN), ("Moon", swe.MOON), ("Mercury", swe.MERCURY), 
                  ("Venus", swe.VENUS), ("Mars", swe.MARS), ("Jupiter", swe.JUPITER), 
                  ("Saturn", swe.SATURN)]
        
        sun_sign = "Unknown"

        for name, body_id in bodies:
            res = swe.calc_ut(jd, body_id)
            sign = get_zodiac_sign(res[0][0])
            try:
                h_pos = swe.house_pos(jd, lat, lon, b'P', res[0][0], 0.0)
                planet_house = f"{int(h_pos)} House"
            except:
                planet_house = "Unknown"

            planets_data.append({"name": name, "sign": sign, "house": planet_house})
            if name == "Sun": sun_sign = sign

        planets_data.append({"name": "Ascendant", "sign": asc_sign, "house": "1 House"})

        return {
            "summary": f"정밀 분석 완료! 당신의 태양 별자리는 {sun_sign}입니다.",
            "planets": planets_data
        }
        
    except Exception as e:
        return {"summary": f"⚠️ 계산 실패: {str(e)}", "planets": []}

# --- [API Endpoints] ---

@app.post("/api/chart")
async def get_chart(request: ChartRequest):
    result = calculate_chart(request.date, request.time, request.city)
    return JSONResponse(content=result)

@app.post("/api/ask")
async def ask_oracle(request: AskRequest):
    """
    [Gemini ONLY] 자체 해석 로직 없이 오직 AI를 통해서만 답변을 생성합니다.
    """
    # 1. API 키 없음 체크
    if not client:
        return JSONResponse(content={
            "answer": "⚠️ 서버에 Gemini API 키가 설정되지 않았습니다. Railway Variables 설정을 확인해주세요."
        })

    q = request.question
    
    chart_context = "User's Birth Chart Data:\n"
    for p in request.planets:
        chart_context += f"- {p.name}: {p.sign} in {p.house}\n"

    # 프롬프트 강화
    prompt = f"""
    당신은 신비롭고 통찰력 있는 전문 점성술사 'Mystic Oracle'입니다.
    아래 제공된 사용자의 출생 차트 데이터를 바탕으로 질문에 대해 깊이 있는 점성술 상담을 제공해주세요.

    [차트 데이터]
    {chart_context}

    [사용자 질문]
    "{q}"

    [답변 가이드라인]
    1. 어조: 신비롭지만 따뜻하고 공감하는 어조 (한국어 존댓말).
    2. 분석: 질문과 관련된 행성의 위치(사인, 하우스)를 구체적으로 언급하며 해석의 근거를 제시하세요.
       - 예: 연애운이면 금성/달, 직업운이면 태양/수성/10하우스 등.
    3. 구조: 가독성 있게 3~4 문단으로 구성하고 핵심 키워드는 강조하세요.
    4. 제한: 차트 데이터에 없는 내용은 지어내지 마세요.
    """

    try:
        # 2. Gemini 호출
        # [수정] 404 오류 해결을 위해 연결이 확인된 'gemini-2.0-flash-exp' 모델로 변경
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt
        )
        return JSONResponse(content={"answer": response.text})
        
    except Exception as e:
        error_msg = str(e)
        print(f"[API Error] Gemini call failed: {error_msg}")
        
        user_msg = f"⚠️ 죄송합니다. AI 연결 중 오류가 발생했습니다.\n(Error: {error_msg})"
        
        # 429 Quota Exceeded (사용량 초과) 처리
        # Experimental 모델은 사용량 제한이 있을 수 있으므로 사용자에게 안내합니다.
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            user_msg = "⚠️ 현재 사용자가 몰려 AI 응답 한도가 초과되었습니다(429). 잠시 후(약 1분 뒤) 다시 시도해주시면 정상적으로 답변을 받으실 수 있습니다."
            
        return JSONResponse(content={"answer": user_msg})

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
