# Deployment & Operational Guide

## 1. Local Development Quickstart

### Prerequisites
- Python 3.12+ (or UV / Conda)
- Node.js 20+ and npm 10+
- Modern Web Browser (Chrome, Edge, Firefox)

### Backend Setup
```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Start backend development server (auto-seeds realistic database on first run)
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
API OpenAPI Swagger documentation will be accessible at: `http://127.0.0.1:8000/docs`

### Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```
The Web Application will be live at: `http://localhost:5173`

---

## 2. Docker Container Deployment

For industrial servers or factory server rooms:

```bash
# Build and start PostgreSQL, Backend API, and Frontend Nginx
docker-compose up --build -d

# Check service health
docker-compose ps

# View backend application logs
docker-compose logs -f backend
```

Access points:
- Frontend Application: `http://<SERVER_IP>:80`
- Backend API & OpenAPI Docs: `http://<SERVER_IP>:8000/docs`
- PostgreSQL Database: `localhost:5432`

---

## 3. Factory Shop-Floor Tablet Setup

1. Connect shop-floor tablets to the factory local area Wi-Fi network.
2. Open tablet browser (Google Chrome recommended) and navigate to `http://<FACTORY_SERVER_IP>`.
3. In browser settings, select **"Add to Home Screen"** to run as a full-screen Progressive Web App (PWA).
4. Log in using `operator` credentials (`operator` / `operator123`).
5. Tablet layout provides large numeric touch-input targets and instant visual feedback (green/amber/red) against active tolerance limits.
