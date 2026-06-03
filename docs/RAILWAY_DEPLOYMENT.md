# Railway Deployment Guide — Bottle Signature Core v1.6.0

This project is a monorepo:

```text
backend/   Python FastAPI API
frontend/  Node.js Express UI
```

Deploy it on Railway as **two services** from the same GitHub repository.

---

## 1. Push to GitHub

From the project root:

```bat
cd C:\1bottle
rmdir /s /q .git
git init
git branch -M main
git add .
git commit -m "Initial commit - Bottle Signature Core v1.6.0"
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
git push -u origin main
```

Do not upload:

```text
backend/venv/
frontend/node_modules/
backend/bottle_signatures.db
```

These are already excluded in `.gitignore`.

---

## 2. Create Backend Service on Railway

1. Railway → New Project → Deploy from GitHub repo.
2. Select this repository.
3. Create a service called:

```text
1bottle-backend
```

4. In service settings, set:

```text
Root Directory: /backend
```

5. Start command should be detected from `backend/railway.json`.

If you need to set manually:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

6. Deploy.

7. Open:

```text
https://your-backend-service.up.railway.app/docs
```

You should see the FastAPI docs.

---

## 3. Create Frontend Service on Railway

1. In the same Railway project, add another GitHub service from the same repository.
2. Create a service called:

```text
1bottle-frontend
```

3. In service settings, set:

```text
Root Directory: /frontend
```

4. Add environment variable:

```text
API_TARGET=https://your-backend-service.up.railway.app
```

Replace with the real backend URL.

5. Start command should be detected from `frontend/railway.json`.

If you need to set manually:

```bash
npm start
```

6. Deploy.

7. Open frontend URL:

```text
https://your-frontend-service.up.railway.app
```

---

## 4. Important Railway Notes

### Backend Storage

The current version uses SQLite:

```text
backend/bottle_signatures.db
```

On Railway, container storage may not be permanent across redeployments unless you attach persistent storage or migrate to PostgreSQL.

For production, move to Railway PostgreSQL.

### API Routing

The frontend calls `/api/...`.

The Node frontend proxies `/api` to:

```text
API_TARGET
```

So the Railway frontend service must have:

```text
API_TARGET=https://your-backend-service.up.railway.app
```

---

## 5. Local Run

### Backend

```bat
start_backend.bat
```

or:

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bat
start_frontend.bat
```

or:

```bash
cd frontend
npm install
npm start
```

Open:

```text
http://localhost:3000
```
