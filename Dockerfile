# 1. 베이스 이미지: Python 3.11 Slim (최신 안정 버전 사용)
# Python 3.9 관련 호환성 경고 해결
FROM python:3.11-slim

# 로그 버퍼링 비활성화 (로그 즉시 출력)
ENV PYTHONUNBUFFERED=1
# Node.js 메모리 설정
ENV NODE_OPTIONS="--max-old-space-size=4096"

# 2. 필수 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    wget \
    build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 3. 작업 디렉토리 설정
WORKDIR /app

# --- [Backend Setup] ---
# 4. 파이썬 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- [Frontend Setup] ---
# 5. React 소스 코드 복사 및 빌드
COPY frontend/package.json ./frontend/
WORKDIR /app/frontend
RUN npm install

# 소스 전체 복사 후 빌드
COPY frontend/ ./
RUN npm run build

# --- [Final Setup] ---
# 6. 다시 루트로 돌아와서 백엔드 코드 복사
WORKDIR /app
COPY backend_main.py .

# 7. 포트 노출
EXPOSE 8000

# 8. 실행 명령어
CMD ["uvicorn", "backend_main:app", "--host", "0.0.0.0", "--port", "8000"]
