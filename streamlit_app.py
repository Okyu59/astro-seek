import streamlit as st
from kerykeion import AstrologicalSubject, KerykeionChartSVG
from datetime import datetime
import os

# --- 1. 페이지 설정 (React 앱처럼 넓게 쓰기) ---
st.set_page_config(
    page_title="My Astro Chart",
    page_icon="🔮",
    layout="wide", # 와이드 모드로 설정하여 대시보드 느낌 연출
    initial_sidebar_state="expanded"
)

# --- 2. 스타일 커스터마이징 (CSS) ---
# Astro-seek 느낌의 깔끔한 폰트와 여백 조정
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    h1, h2, h3 {
        font-family: 'Helvetica Neue', sans-serif;
        color: #2c3e50;
    }
    .stButton>button {
        width: 100%;
        background-color: #4e73df;
        color: white;
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 사이드바 (사용자 입력) ---
with st.sidebar:
    st.header("📝 정보 입력")
    name = st.text_input("이름 (영문)", value="Guest")
    
    col1, col2 = st.columns(2)
    with col1:
        year = st.number_input("년", 1950, 2025, 1990)
        month = st.number_input("월", 1, 12, 1)
        day = st.number_input("일", 1, 31, 1)
    with col2:
        hour = st.number_input("시 (24시)", 0, 23, 12)
        minute = st.number_input("분", 0, 59, 0)
    
    st.markdown("---")
    st.subheader("📍 위치 정보")
    city = st.text_input("도시 (영문)", value="
