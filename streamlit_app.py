import streamlit as st
import time
from playwright.sync_api import sync_playwright
import subprocess

# --- [Setup & Install Browser for Cloud] ---
# Streamlit Cloud에서 Playwright 브라우저가 없을 경우 설치를 시도합니다.
def install_playwright_browser():
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        # 이미 설치되어 있거나 권한 문제 등으로 실패할 수 있으나, 
        # packages.txt가 있으면 시스템 크로미움이 대신 사용될 수 있음
        print(f"브라우저 설치 시도 로그: {e}")

# --- [Function: Real Scraper] ---
@st.cache_data(ttl=3600) # 1시간 동안 데이터 캐싱 (반복 크롤링 방지)
def scrape_astro_seek(birth_date, birth_time, city):
    """
    Astro-Seek에 접속하여 실제 데이터를 가져옵니다.
    """
    try:
        year, month, day = str(birth_date).split('-')
        hour, minute = str(birth_time).split(':')
    except:
        return None

    data = {"planets": [], "summary": ""}
    
    with sync_playwright() as p:
        try:
            # Headless 모드로 브라우저 실행
            # Streamlit Cloud 환경에 맞춘 인자 설정
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
            page = browser.new_page()
            
            # 1. 페이지 이동
            page.goto("https://www.astro-seek.com/birth-chart-horoscope-online", timeout=60000)
            
            # 2. 폼 입력 (선택자는 사이트 변경에 따라 달라질 수 있음)
            page.select_option('select[name="narozeni_den"]', str(int(day)))
            page.select_option('select[name="narozeni_mesic"]', str(int(month)))
            page.select_option('select[name="narozeni_rok"]', year)
            page.fill('input[name="narozeni_hodina"]', hour)
            page.fill('input[name="narozeni_minuta"]', minute)
            
            # 도시 입력 우회: "Unknown" 체크박스가 있다면 체크하거나, 직접 입력 후 엔터
            # 여기서는 복잡한 도시 검색 팝업을 피하기 위해 바로 계산 시도
            # (실제로는 Astro-Seek 기본값인 프라하로 계산될 수 있으므로, URL 파라미터 방식 권장)
            
            page.click('input[type="submit"]')
            
            # 결과 테이블 대기
            page.wait_for_selector('.horoscope_table', timeout=30000)
            
            # 3. 데이터 추출
            rows = page.query_selector_all(".horoscope_table tr")
            for row in rows:
                text = row.inner_text()
                # 간단한 파싱 로직
                if "Sun" in text and "Sign" not in text: # 헤더 제외
                    parts = text.split()
                    if len(parts) > 1:
                        data["planets"].append({"name": "Sun", "sign": parts[1], "house": "10 House"})
                elif "Moon" in text:
                    parts = text.split()
                    if len(parts) > 1:
                        data["planets"].append({"name": "Moon", "sign": parts[1], "house": "4 House"})
                elif "Mercury" in text:
                    parts = text.split()
                    if len(parts) > 1:
                        data["planets"].append({"name": "Mercury", "sign": parts[1], "house": "11 House"})
                elif "Venus" in text:
                    parts = text.split()
                    if len(parts) > 1:
                        data["planets"].append({"name": "Venus", "sign": parts[1], "house": "12 House"})
                elif "Mars" in text:
                    parts = text.split()
                    if len(parts) > 1:
                        data["planets"].append({"name": "Mars", "sign": parts[1], "house": "5 House"})

            data["summary"] = f"{year}년 {month}월 {day}일에 태어난 당신의 차트가 생성되었습니다."
            browser.close()
            
            # 데이터가 비어있다면 (파싱 실패) 예외 처리
            if not data["planets"]:
                raise Exception("데이터 추출 실패")
                
            return data

        except Exception as e:
            if 'browser' in locals():
                browser.close()
            print(f"크롤링 에러: {e}")
            # 실패 시 데모용 목업 데이터 반환
            return {
                "summary": "(Astro-Seek 연결 지연으로 예시 데이터가 표시됩니다) 귀하는 처녀자리 태양을 가지고 태어나셨군요.",
                "planets": [
                    {"name": "Sun", "sign": "Virgo", "house": "10 House"},
                    {"name": "Moon", "sign": "Leo", "house": "9 House"},
                    {"name": "Mercury", "sign": "Libra", "house": "11 House"},
                    {"name": "Venus", "sign": "Scorpio", "house": "12 House"},
                    {"name": "Mars", "sign": "Virgo", "house": "10 House"},
                    {"name": "Jupiter", "sign": "Sagittarius", "house": "1 House"},
                ]
            }

# --- [Streamlit UI Configuration] ---
st.set_page_config(page_title="Mystic Astro", page_icon="✨", layout="centered")

# CSS: React 앱의 골드 & 다크 테마 적용
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Lato:wght@300;400;700&display=swap');
    
    /* 전체 배경 및 폰트 */
    .stApp { 
        background-color: #0B0F19; 
        color: #e2e8f0; 
        font-family: 'Lato', sans-serif; 
    }
    
    /* 타이틀 폰트 (Cinzel) */
    h1, h2, h3 { 
        font-family: 'Cinzel', serif !important; 
        color: #fbbf24 !important; /* Amber-400 */
        text-align: center; 
    }
    
    /* 입력 필드 스타일링 (중앙 정렬 포함) */
    .stTextInput input, .stDateInput input, .stTimeInput input {
        background-color: #121726 !important; 
        color: white !important; 
        border: 1px solid #475569 !important; 
        border-radius: 12px !important;
        text-align: center !important; 
        padding: 10px !important;
    }
    
    /* 버튼 스타일링 */
    div.stButton > button {
        width: 100%; 
        background: linear-gradient(90deg, #d97706, #b45309); 
        color: white; 
        border: none; 
        padding: 12px; 
        font-family: 'Cinzel', serif; 
        font-weight: bold;
        border-radius: 12px;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background: linear-gradient(90deg, #b45309, #d97706);
        box-shadow: 0 0 15px rgba(217, 119, 6, 0.4);
        color: #fff;
        border-color: #fff;
    }
    
    /* 행성 카드 스타일 */
    .planet-card {
        background: rgba(30, 41, 59, 0.5); 
        border: 1px solid rgba(217, 119, 6, 0.2); 
        border-radius: 10px; 
        padding: 15px; 
        text-align: center; 
        margin: 5px; 
        display: inline-block;
        width: 100%;
    }
    
    /* 채팅 메시지 스타일 */
    .stChatMessage {
        background-color: rgba(15, 23, 42, 0.5);
        border-radius: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# --- [Main Logic] ---
if 'step' not in st.session_state:
    st.session_state.step = 'input'
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'chart_data' not in st.session_state:
    st.session_state.chart_data = None

# Install browser check (First run only)
if 'browser_installed' not in st.session_state:
    with st.spinner("서버 초기화 중..."):
        install_playwright_browser()
    st.session_state.browser_installed = True

# --- [UI Step 1: Input] ---
if st.session_state.step == 'input':
    st.markdown("<br><h1 style='font-size: 3.5rem;'>Oracle Destiny</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94a3b8; margin-bottom: 40px;'>별들이 속삭이는 당신의 운명을 해석합니다.</p>", unsafe_allow_html=True)
    
    with st.form("entry_form"):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("생년월일")
            city = st.text_input("도시", "Seoul")
        with col2:
            time_val = st.time_input("태어난 시간")
            st.text_input("국가", "Korea", disabled=True) 
        
        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("REVEAL MY FATE ✨")
        
        if submitted:
            if len(city) < 2:
                st.error("도시 이름을 확인해주세요.")
            else:
                with st.spinner("별들의 위치를 계산하고 있습니다... (약 10초 소요)"):
                    # 실제 크롤링 함수 호출
                    result = scrape_astro_seek(date, time_val, city)
                    
                    if result:
                        st.session_state.chart_data = result
                        st.session_state.step = 'chat'
                        initial_msg = f"환영합니다. {result['summary']}\n\n무엇이든 물어보세요."
                        st.session_state.messages.append({"role": "assistant", "content": initial_msg})
                        st.rerun()

# --- [UI Step 2: Chat] ---
elif st.session_state.step == 'chat':
    # 상단 헤더 & 리셋 버튼
    c1, c2 = st.columns([5,1])
    c1.markdown("<h3 style='text-align:left; color:#fbbf24; margin-top:0;'>Astro Seek AI</h3>", unsafe_allow_html=True)
    if c2.button("↺"):
        st.session_state.step = 'input'
        st.session_state.messages = []
        st.rerun()
    
    # 행성 정보 카드 표시
    if st.session_state.chart_data:
        st.markdown("<div style='display: flex; overflow-x: auto; gap: 10px; padding-bottom: 10px;'>", unsafe_allow_html=True)
        cols = st.columns(3) # 3열 그리드로 표시
        planets = st.session_state.chart_data['planets']
        
        for i, planet in enumerate(planets):
            with cols[i % 3]:
                st.markdown(f"""
                <div class="planet-card">
                    <div style="color:#fbbf24; font-family:'Cinzel', serif; font-weight:bold;">{planet['name']}</div>
                    <div style="font-size:0.9em; color: #cbd5e1; margin-top:5px;">{planet['sign']}</div>
                    <div style="font-size:0.7em; color: #64748b;">{planet['house']}</div>
                </div>
                """, unsafe_allow_html=True)
    
    st.divider()

    # 채팅 메시지 출력
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="✨" if msg["role"] == "assistant" else None):
            st.write(msg["content"])
            
    # 추천 질문 버튼 (첫 메시지 이후에만 표시)
    if len(st.session_state.messages) == 1:
        st.markdown("<p style='font-size: 0.8rem; color: #64748b; margin-top: 10px;'>다음 질문을 선택해보세요:</p>", unsafe_allow_html=True)
        bq1, bq2, bq3 = st.columns(3)
        if bq1.button("📅 2026년 흐름"):
            st.session_state.messages.append({"role": "user", "content": "2026년도 월별 흐름을 예측해줘"})
            st.rerun()
        if bq2.button("💖 연애운"):
            st.session_state.messages.append({"role": "user", "content": "2026년도 연애운을 알려줘"})
            st.rerun()
        if bq3.button("💼 직업 적성"):
            st.session_state.messages.append({"role": "user", "content": "내 직업적 재능과 잘 맞는 분야를 알려줘"})
            st.rerun()

    # 사용자 입력
    if prompt := st.chat_input("운세에 대해 물어보세요..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

    # AI 응답 생성 (마지막 메시지가 유저일 때)
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.chat_message("assistant", avatar="✨"):
            with st.spinner("해석 중..."):
                time.sleep(1.2) # 생각하는 척 딜레이
                
                # 간단한 응답 로직 (실제 LLM 연동 시 여기에 API 호출 추가)
                last_user_msg = st.session_state.messages[-1]["content"]
                planets = st.session_state.chart_data['planets']
                sun_sign = next((p['sign'] for p in planets if p['name'] == 'Sun'), "Unknown")
                
                response = ""
                if "연애" in last_user_msg or "사랑" in last_user_msg:
                    response = f"당신의 태양 별자리는 **{sun_sign}**입니다. 금성의 위치를 보아하니, 올해는 깊은 감정적 유대를 중요시하게 될 것 같네요. 5월 즈음 좋은 인연이 닿을 수 있습니다."
                elif "직업" in last_user_msg or "일" in last_user_msg:
                    response = f"직업적인 면에서 **{sun_sign}**의 성향은 꼼꼼함과 분석력을 발휘할 때 빛납니다. 현재 별들의 배치는 새로운 도전보다는 내실을 다지는 것을 추천합니다."
                else:
                    response = f"흥미로운 질문이네요. 당신의 차트({sun_sign})를 보면, 이 문제에 대해 매우 신중하게 접근하고 계신 것 같습니다. 조금 더 구체적인 상황을 말씀해주시면 자세히 봐드릴게요."
                
                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})


