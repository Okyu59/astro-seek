from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

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

@app.post("/api/chart")
async def get_chart(request: ChartRequest):
    # 테스트용 더미 데이터 반환 (크롤링 부하 없이 UI 통신 확인용)
    return {
        "summary": "서버 연결에 성공했습니다! 이 메시지가 보이면 통신은 정상입니다.",
        "planets": [
            {"name": "Sun", "sign": "Test Sign", "house": "1 House"},
            {"name": "Moon", "sign": "Test Sign", "house": "2 House"}
        ]
    }

# --- 프론트엔드 파일 서빙 ---
DIST_DIR = os.path.join(os.getcwd(), "frontend/dist")
ASSETS_DIR = os.path.join(DIST_DIR, "assets")

# 1. assets 폴더 마운트 (JS, CSS)
if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

# 2. 루트 경로 접속 시 index.html 반환
@app.get("/")
async def serve_index():
    index_path = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return "Error: index.html not found. Build failed."

# 3. 그 외 모든 경로 index.html로 리다이렉트 (SPA 지원)
@app.exception_handler(404)
async def not_found_handler(request, exc):
    index_path = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return "Error: 404 and build missing"


