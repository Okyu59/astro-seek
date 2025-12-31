# 1. 베이스 이미지: Python 3.9 Slim
FROM python:3.9-slim

# 2. 필수 패키지 및 Node.js 설치 (React 빌드용)
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    wget \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 3. 작업 디렉토리 설정
WORKDIR /app

# --- [Backend Setup] ---
# 4. 파이썬 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Playwright 브라우저 설치
RUN playwright install chromium
RUN playwright install-deps chromium

# --- [Frontend Setup] ---
# 6. React 소스 코드 복사 및 빌드
# 중요: package-lock.json 복사 라인을 제거했습니다.
COPY frontend/package.json ./frontend/
WORKDIR /app/frontend
RUN npm install

# 소스 전체 복사 후 빌드
COPY frontend/ ./
RUN npm run build

# --- [Final Setup] ---
# 7. 다시 루트로 돌아와서 백엔드 코드 복사
WORKDIR /app
COPY backend_main.py .

# 8. 포트 노출
EXPOSE 8000

# 9. 실행 명령어
CMD ["uvicorn", "backend_main:app", "--host", "0.0.0.0", "--port", "8000"]


