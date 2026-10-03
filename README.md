# Luma — AI Study Assistant

Dự án Hackathon **AI Study Assistant** gồm 5 module độc lập, được phát triển song song và ghép qua các contract rõ ràng.

## Demo nhanh

**GitHub Pages:** https://nguyendoan30.github.io/hackathon/

> Workflow GitHub Pages trên `main` đã build và deploy thành công.

## Cấu trúc dự án

| Thư mục | Phụ trách | Chức năng chính |
|---|---|---|
| `frontend/` | Frontend | Giao diện Next.js/React/TypeScript, thư viện bài học, Tutor, Summary, Flashcard, Quiz, Progress |
| `backend/` | Backend / Database | FastAPI, SQLite, Auth, API, upload, persistence, tích hợp các module |
| `ai_smart_context/` | AI / Smart Context | Retrieval, context, prompt, AI Tutor, Summary, Gemini/Mock provider |
| `file_processing/` | File Processing | PDF, OCR ảnh, audio/transcript, chuẩn hóa nội dung |
| `learning/` | Learning | Flashcard, Quiz, grading, learning progress |

## Backend / Database

Backend dùng **FastAPI + SQLite** và có demo độc lập chạy local.

### Chạy demo backend trên Windows

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
powershell -ExecutionPolicy Bypass -File .\run-demo.ps1
```

Mở:

- Demo backend: http://127.0.0.1:8765/demo
- Swagger API: http://127.0.0.1:8765/docs
- Health check: http://127.0.0.1:8765/health

Tài khoản demo:

- Email: `demo@studyassistant.dev`
- Password: `DemoStudy!2026`

Backend có các nhóm chức năng: authentication, lessons, documents/upload, summary, AI Tutor, flashcards, quiz, progress, database persistence và kiểm tra quyền truy cập.

Chi tiết: [backend/README.md](backend/README.md)

## Chạy frontend

```bash
cd frontend
npm ci
npm run dev
```

Mở http://127.0.0.1:3100

Chi tiết: [frontend/README.md](frontend/README.md)

## Các module tích hợp

- AI / Smart Context: [ai_smart_context/README.md](ai_smart_context/README.md)
- File Processing: [file_processing/README.md](file_processing/README.md)
- Learning / Quiz / Flashcard / Progress: [learning/README.md](learning/README.md)

## Kiến trúc tích hợp

```text
Frontend
   |
   v
FastAPI Backend  <----> SQLite
   |
   +---- AI / Smart Context
   |
   +---- File Processing
   |
   +---- Learning / Quiz / Flashcard / Progress
```

Backend là lớp trung tâm chịu trách nhiệm xác thực, phân quyền, lưu dữ liệu và điều phối các provider. Các module còn lại giữ ranh giới riêng để tránh xung đột khi nhiều thành viên cùng phát triển.

## Công nghệ

- Frontend: Next.js, React, TypeScript
- Backend: FastAPI, Python
- Database: SQLite
- AI: Gemini-compatible provider + Smart Context/Retrieval
- File processing: PDF parsing, OCR, speech-to-text
- Testing: pytest / unittest
- Deployment demo: GitHub Pages

## Repository

https://github.com/NguyenDoan30/hackathon


## Chạy AI thật với Gemini

Repo đã có sẵn module AI thật tại `ai_smart_context/` và backend adapter tại `ai_smart_context.backend_adapter:BackendAIProvider`.

1. Copy `ai_smart_context/.env.example` thành `ai_smart_context/.env`.
2. Điền `GEMINI_API_KEY` thật và giữ `GEMINI_MODEL=gemini-2.5-flash` nếu tài khoản hỗ trợ model này.
3. Khi chạy backend production, cấu hình:

```env
APP_MODE=production
AI_PROVIDER=ai_smart_context.backend_adapter:BackendAIProvider
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
GEMINI_MODEL=gemini-2.5-flash
CORS_ORIGINS=https://nguyendoan30.github.io
```

Không commit API key thật vào repository public. GitHub Pages chỉ host frontend tĩnh; AI thật cần backend Python đang chạy.
