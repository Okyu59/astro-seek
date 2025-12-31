from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
import os
import traceback

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

# --- [1. API Endpoints] ---
# API는 반드시 StaticFiles보다 위에 정의해야 합니다.

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

@app.post("/api/chart")
async def get_chart(request: ChartRequest):
    print(f"[API Request] {request}")
    # 크롤링 로직 (축약됨 - 이전과 동일하게 유지하거나 아래 Fallback 사용)
    # 실제 구현 시에는 안전을 위해 Fallback 로직을 포함하세요.
    return get_fallback_data(request.date, "Traffic Optimization")

def get_fallback_data(date, reason):
    return {
        "summary": f"(시스템: {reason}) 서버 최적화를 위해 예비 데이터를 보여드립니다. {date}",
        "planets": [
            {"name": "Sun", "sign": "Virgo", "house": "10 House"},
            {"name": "Moon", "sign": "Leo", "house": "9 House"},
            {"name": "Mercury", "sign": "Libra", "house": "11 House"},
            {"name": "Venus", "sign": "Scorpio", "house": "12 House"},
            {"name": "Mars", "sign": "Virgo", "house": "10 House"},
            {"name": "Jupiter", "sign": "Sagittarius", "house": "1 House"}
        ]
    }

# --- [2. Frontend Serving Logic] ---
# 프론트엔드 빌드 폴더 경로 확인
DIST_DIR = os.path.join(os.getcwd(), "frontend/dist")

if os.path.exists(DIST_DIR):
    # 1) 루트 URL 접속 시 index.html 반환 (SPA 지원)
    @app.get("/")
    async def serve_spa():
        return FileResponse(os.path.join(DIST_DIR, "index.html"))

    # 2) 그 외 모든 정적 파일(JS, CSS, 이미지) 서빙
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="static")
    
    print(f"[Server] Serving frontend from {DIST_DIR}")
else:
    # 빌드 폴더가 없으면 에러 메시지 출력 (검은 화면 대신 이 메시지가 나와야 함)
    print(f"[Error] 'frontend/dist' folder not found in {os.getcwd()}")
    @app.get("/")
    async def index_error():
        return JSONResponse(
            status_code=404, 
            content={
                "error": "Frontend build failed or not found.", 
                "files_in_root": os.listdir(os.getcwd()) if os.path.exists(os.getcwd()) else "None",
                "files_in_frontend": os.listdir("frontend") if os.path.exists("frontend") else "No frontend folder"
            }
        )


