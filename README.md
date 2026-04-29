# CoachX Media AI — 골프 레슨 영상 편집기

골프 코치가 학생의 레슨 영상을 자동으로 편집해주는 웹 애플리케이션입니다.

## 주요 기능

| 기능 | 설명 |
|------|------|
| 📹 **비교 영상** | 레슨 전/후 영상을 좌우 화면 분할(Side-by-side)로 합성 |
| ✂️ **요약 영상** | 전체 레슨 영상에서 원하는 구간을 선택해 하이라이트 요약 영상 생성 |

## 기술 스택

- **Backend**: Python · Flask
- **Video Processing**: MoviePy (ffmpeg 기반)
- **Frontend**: Bootstrap 5 · Vanilla JS (드래그앤드롭 업로드, 타임라인 클립 편집기)

## 설치 및 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 서버 실행
python app.py
```

브라우저에서 `http://localhost:5000` 접속

## 지원 형식

업로드 가능한 영상 형식: **MP4, MOV, AVI, MKV, WEBM** (파일당 최대 500 MB)

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/` | 메인 페이지 |
| `POST` | `/api/comparison` | 비교 영상 생성 (`before_video`, `after_video`) |
| `POST` | `/api/summary` | 요약 영상 생성 (`lesson_video`, `clips` JSON) |
| `POST` | `/api/video-info` | 영상 정보 조회 (`video`) |
| `GET` | `/download/<filename>` | 생성된 영상 다운로드 |
