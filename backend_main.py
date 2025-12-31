from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
import os

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- [로깅 미들웨어] ---
# 요청이 들어올 때마다 로그를 남겨서 Railway Logs에서 확인할 수 있게 함
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"[Request] {request.method} {request.url.path}")
    response = await call_next(request)
    print(f"[Response] {response.status_code}")
    return response

# 데이터 모델
class ChartRequest(BaseModel):
    date: str
    time: str
    city: str

# --- [API Endpoints] ---
@app.post("/api/chart")
async def get_chart(request: ChartRequest):
    print(f"[API] Chart Request: {request}")
    # (안전장치) 크롤링 로직 대신 일단 Fallback 데이터를 반환하여 앱 작동 확인
    return {
        "summary": "서버 연결 성공! (실제 크롤링은 로직 복원 필요)",
        "planets": [
            {"name": "Sun", "sign": "Virgo", "house": "10 House"},
            {"name": "Moon", "sign": "Leo", "house": "9 House"},
            {"name": "Mercury", "sign": "Libra", "house": "11 House"},
            {"name": "Venus", "sign": "Scorpio", "house": "12 House"},
            {"name": "Mars", "sign": "Virgo", "house": "10 House"},
            {"name": "Jupiter", "sign": "Sagittarius", "house": "1 House"}
        ]
    }

# --- [Frontend Serving Logic (SPA Optimized)] ---
CURRENT_DIR = os.getcwd()
DIST_DIR = os.path.join(CURRENT_DIR, "frontend/dist")
ASSETS_DIR = os.path.join(DIST_DIR, "assets")

# 1. Assets 폴더가 있다면 우선적으로 마운트 (JS, CSS 파일용)
if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
    print(f"[Startup] Assets mounted from {ASSETS_DIR}")
else:
    print(f"[Startup] Warning: Assets folder not found at {ASSETS_DIR}")

# 2. 루트 및 기타 모든 경로에 대해 index.html 반환 (Catch-All)
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    index_path = os.path.join(DIST_DIR, "index.html")
    
    # API 요청은 위에서 처리되므로 여기까지 오지 않음
    # 파일이 존재하면 index.html 반환
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    # 빌드 실패 시 에러 JSON 반환
    return JSONResponse(
        status_code=404,
        content={
            "error": "Frontend build not found.",
            "message": "Please check 'npm run build' logs.",
            "current_dir": CURRENT_DIR,
            "dist_exists": os.path.exists(DIST_DIR)
        }
    )


