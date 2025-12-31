from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
from datetime import datetime, timedelta

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

# --- [점성술 해석 데이터베이스] ---
# 간단한 키워드 기반 해석 엔진
ASTRO_DB = {
    "signs": {
        "Aries": {"kwd": "용기있고 주도적인", "love": "불꽃처럼 뜨겁고 직설적인", "work": "새로운 길을 개척하는 리더형"},
        "Taurus": {"kwd": "신중하고 감각적인", "love": "변함없고 신뢰할 수 있는", "work": "안정과 결과를 중요시하는 실리형"},
        "Gemini": {"kwd": "호기심 많고 재치있는", "love": "대화가 잘 통하고 유쾌한", "work": "다양한 정보를 다루는 멀티태스커"},
        "Cancer": {"kwd": "감수성이 풍부하고 보호적인", "love": "헌신적이고 깊은 공감을 나누는", "work": "팀워크와 돌봄에 능한"},
        "Leo": {"kwd": "자신감 넘치고 열정적인", "love": "드라마틱하고 로맨틱한", "work": "주목받는 무대나 창조적인 분야"},
        "Virgo": {"kwd": "섬세하고 분석적인", "love": "배려심 깊고 현실적인", "work": "완벽함을 추구하는 전문가형"},
        "Libra": {"kwd": "조화롭고 사교적인", "love": "세련되고 매너있는", "work": "중재와 협상을 잘하는 파트너형"},
        "Scorpio": {"kwd": "통찰력 있고 강렬한", "love": "영혼까지 공유하는 깊은", "work": "본질을 꿰뚫어보는 탐구형"},
        "Sagittarius": {"kwd": "자유롭고 철학적인", "love": "함께 모험을 떠날 수 있는", "work": "비전을 제시하는 이상가형"},
        "Capricorn": {"kwd": "성실하고 야망있는", "love": "책임감 있고 진중한", "work": "목표를 반드시 달성하는 전략가형"},
        "Aquarius": {"kwd": "독창적이고 이성적인", "love": "친구 같으면서도 존중받는", "work": "기존의 틀을 깨는 혁신가형"},
        "Pisces": {"kwd": "직관적이고 몽환적인", "love": "낭만적이고 희생적인", "work": "예술적 영감과 치유 능력이 있는"}
    },
    "planets": {
        "Sun": "자아와 인생의 목표",
        "Moon": "무의식과 감정",
        "Mercury": "지성과 의사소통",
        "Venus": "사랑과 미적 가치관",
        "Mars": "행동력과 열정",
        "Jupiter": "행운과 확장",
        "Saturn": "책임과 시련"
    }
}

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
    사용자의 질문과 차트 정보를 받아 맞춤형 해석을 생성하는 엔드포인트
    """
    q = request.question
    planets = {p.name: p for p in request.planets} # 검색 쉽게 변환
    
    response_text = ""
    
    # 1. 질문 키워드 분석 및 행성 매핑
    target_planets = []
    category = "general"
    
    if any(k in q for k in ["연애", "사랑", "남자", "여자", "결혼", "인연"]):
        target_planets = ["Venus", "Moon", "Mars"]
        category = "love"
        response_text += "💖 사랑과 인연의 흐름을 읽어드릴게요.\n\n"
        
    elif any(k in q for k in ["직업", "일", "돈", "성공", "진로", "적성"]):
        target_planets = ["Sun", "Mercury", "Saturn", "Mars"]
        category = "work"
        response_text += "💼 당신의 직업적 잠재력을 살펴볼게요.\n\n"
        
    elif any(k in q for k in ["성격", "나", "자아", "심리"]):
        target_planets = ["Sun", "Moon", "Ascendant"]
        category = "personality"
        response_text += "✨ 당신의 내면과 본질을 들여다봅니다.\n\n"
        
    elif any(k in q for k in ["2026", "내년", "운세", "미래"]):
        # 운세는 트랜짓 계산이 필요하나 여기선 네이탈 기반 조언으로 대체
        target_planets = ["Jupiter", "Saturn"]
        category = "future"
        response_text += "📅 2026년의 흐름을 예측해봅니다.\n\n"
    
    else:
        target_planets = ["Sun", "Moon"]
        response_text += "🔮 별들의 메시지를 전해드립니다.\n\n"

    # 2. 해석 생성 로직
    for p_name in target_planets:
        if p_name not in planets: continue
        
        p_data = planets[p_name]
        sign_info = ASTRO_DB["signs"].get(p_data.sign, {})
        
        # 행성별 역할 설명
        role = ASTRO_DB["planets"].get(p_name, "")
        
        # 별자리 특성
        trait = sign_info.get("kwd", "")
        detail = sign_info.get(category if category in ["love", "work"] else "kwd", "")
        
        response_text += f"• **{p_name} ({p_data.sign})**: {role}을(를) 의미합니다. 당신은 이 부분에서 **{trait}** 성향을 보이며, 특히 {category if category in ['love', 'work'] else '삶'}에 있어서 **{detail}** 태도를 취하게 됩니다.\n"

    # 3. 마무리 조언
    if category == "love":
        venus_sign = planets.get("Venus", {}).get("sign", "")
        response_text += f"\n💡 조언: 당신의 금성이 {venus_sign}에 있으므로, 감정을 숨기기보다 솔직하게 표현할 때 진정한 인연을 만날 수 있습니다."
    elif category == "work":
        sun_sign = planets.get("Sun", {}).get("sign", "")
        response_text += f"\n💡 조언: 태양 별자리인 {sun_sign}의 강점을 살려, {ASTRO_DB['signs'][sun_sign]['work']} 분야에 도전해보세요."
    elif category == "future":
        response_text += "\n💡 2026년은 목성의 영향으로 확장의 기회가 옵니다. 준비된 자에게 행운이 따를 것입니다."
        
    return JSONResponse(content={"answer": response_text})

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
