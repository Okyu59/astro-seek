from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
from datetime import datetime, timedelta
import google.generativeai as genai # [추가] Gemini API 라이브러리

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

# [설정] Gemini API 키 설정
# Railway 배포 시 Variables 탭에서 GEMINI_API_KEY를 추가해야 합니다.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # 빠르고 효율적인 Flash 모델 사용 권장
        model = genai.GenerativeModel('gemini-1.5-flash')
        print("[System] Gemini API Configured successfully.")
    except Exception as e:
        print(f"[System] Gemini Configuration Error: {e}")
        model = None
else:
    print("[System] Warning: GEMINI_API_KEY not found in environment variables.")
    model = None

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
    planets: list[PlanetData] # 질문 시 차트 정보를 함께 받음

def get_zodiac_sign(longitude):
    """황경(0~360도)을 별자리 이름으로 변환"""
    signs = [
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ]
    index = int(longitude / 30)
    return signs[index % 12]

def calculate_chart(birth_date, birth_time, city):
    if not LIBRARY_LOADED:
        return {
            "summary": f"⚠️ 서버 설정 오류: pyswisseph 로드 실패\n({IMPORT_ERROR})\nrequirements.txt 확인 필요",
            "planets": []
        }

    try:
        # 날짜/시간 파싱
        year, month, day = map(int, birth_date.split('-'))
        hour, minute = map(int, birth_time.split(':'))
        
        # UTC 변환 (KST -> UTC)
        dt_kst = datetime(year, month, day, hour, minute)
        dt_utc = dt_kst - timedelta(hours=9)
        hour_decimal = dt_utc.hour + (dt_utc.minute / 60.0) + (dt_utc.second / 3600.0)
        
        # Swiss Ephemeris 계산
        jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour_decimal)
        lat, lon = 37.56, 126.97 # 서울 좌표 고정 (실제 앱에선 city기반 매핑 필요)
        
        # 하우스 및 상승궁
        cusps, ascmc = swe.houses(jd, lat, lon, b'P')
        asc_sign = get_zodiac_sign(ascmc[0])
        
        planets_data = []
        bodies = [("Sun", swe.SUN), ("Moon", swe.MOON), ("Mercury", swe.MERCURY), 
                  ("Venus", swe.VENUS), ("Mars", swe.MARS), ("Jupiter", swe.JUPITER), 
                  ("Saturn", swe.SATURN)]
        
        sun_sign = "Unknown"

        for name, body_id in bodies:
            res = swe.calc_ut(jd, body_id)
            longitude = res[0][0]
            sign = get_zodiac_sign(longitude)
            
            try:
                h_pos = swe.house_pos(jd, lat, lon, b'P', longitude, 0.0)
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
    [Gemini 연동] 사용자의 질문과 차트 정보를 바탕으로 AI 점성술사가 답변을 생성합니다.
    """
    # 1. API 키 확인
    if not model:
        return JSONResponse(content={
            "answer": "⚠️ 죄송합니다. 현재 서버에 AI 설정(API Key)이 되어있지 않아 상세한 상담이 어렵습니다. 관리자에게 문의해주세요."
        })

    # 2. 프롬프트 구성
    q = request.question
    
    # 차트 데이터를 텍스트로 변환
    chart_context = "User's Birth Chart Data:\n"
    for p in request.planets:
        chart_context += f"- {p.name}: {p.sign} in {p.house}\n"

    prompt = f"""
    당신은 신비롭고 통찰력 있는 전문 점성술사 'Mystic Oracle'입니다.
    아래 제공된 사용자의 출생 차트(Birth Chart) 데이터를 바탕으로 사용자의 질문에 답변해주세요.

    [차트 데이터]
    {chart_context}

    [사용자 질문]
    "{q}"

    [답변 가이드라인]
    1. 말투: 신비롭고 따뜻하며, 전문적인 점성술사의 어조를 유지하세요. (존댓말 사용)
    2. 내용: 질문과 관련된 특정 행성이나 하우스의 위치를 근거로 들어 구체적으로 해석해주세요.
       - 예: 연애운 질문이면 금성(Venus)과 5하우스/7하우스를 언급.
       - 예: 직업운 질문이면 태양(Sun), 수성(Mercury), 10하우스를 언급.
    3. 형식: 너무 길지 않게, 3~4문단의 읽기 편한 길이로 작성해주세요. 중요한 키워드는 강조해도 좋습니다.
    4. 공감: 사용자의 고민에 공감하고 긍정적인 방향을 제시해주세요.
    """

    try:
        # 3. Gemini에게 답변 요청
        response = model.generate_content(prompt)
        return JSONResponse(content={"answer": response.text})
        
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return JSONResponse(content={
            "answer": "죄송합니다. 별들의 목소리를 듣는 중에 잠시 잡음이 발생했습니다. 잠시 후 다시 물어봐주시겠어요?"
        })

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
