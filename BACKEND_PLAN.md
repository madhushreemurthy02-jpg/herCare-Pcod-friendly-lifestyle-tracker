# herCare 🌸 — Backend Implementation Plan

> **Created:** 4 April 2026  
> **Status:** Planning  
> **Stack:** Python 3.10+ · Flask · MongoDB · JWT · Gemini AI

---

## Frontend Status ✅

All 6 pages are built with consistent sakura-themed UI:

| Page | File | Status | Backend Wiring |
|------|------|--------|----------------|
| Sign In | `signin.html` | ✅ Built | ✅ Calls `POST /api/auth/login` (localStorage fallback) |
| Sign Up | `signup.html` | ✅ Built | ✅ Calls `POST /api/auth/register` (localStorage fallback) |
| Health Profile | `profile.html` | ✅ Built | ❌ Saves locally only — needs API calls |
| Daily Log | `daily.html` | ✅ Built | ❌ Saves locally only — needs API calls |
| Cycle Tracker | `cycletracker.html` | ✅ Built | ❌ Saves locally only — needs API calls |
| AI Insights | `insight.html` | ✅ Built | ❌ Static insights only — needs Gemini AI integration |

### Known Frontend Bugs
1. `signin.html` L334 — `.value.trim` should be `.value.trim()` (missing parentheses)
2. `signup.html` L365 — `getElementById('phone')` fails, phone input has no `id`, only `name="phone"`
3. Navigation links are inconsistent across pages (some point to `#`, filenames don't match)

---

## Backend Architecture

```
hercare-backend/
├── app.py                    # Flask app entry point
├── config.py                 # MongoDB URI, JWT secret, etc.
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (secrets, API keys)
│
├── models/                   # MongoDB document schemas
│   ├── __init__.py
│   ├── user.py               # User model (name, email, password hash)
│   ├── health_profile.py     # Age, height, weight, cycle info
│   ├── daily_log.py          # Sleep, hydration, mood, nutrition, activity
│   └── cycle_log.py          # Period dates, symptoms, flow, pain
│
├── routes/                   # API blueprints
│   ├── __init__.py
│   ├── auth.py               # POST /api/auth/register, /api/auth/login
│   ├── profile.py            # GET/PUT /api/profile
│   ├── daily_log.py          # POST/GET /api/daily-log
│   ├── cycle.py              # POST/GET /api/cycle
│   └── insights.py           # POST /api/insights (Gemini AI call)
│
└── middleware/
    ├── __init__.py
    └── auth_middleware.py     # JWT token verification decorator
```

---

## API Endpoints

### 1. Auth Routes

| Method | Endpoint | Request Body | Response |
|--------|----------|-------------|----------|
| `POST` | `/api/auth/register` | `{ first_name, last_name, email, password, phone }` | `{ success, token, user: { id, first_name }, message }` |
| `POST` | `/api/auth/login` | `{ email, password }` | `{ success, token, user: { id, first_name }, message }` |

### 2. Profile Routes

| Method | Endpoint | Request Body | Response |
|--------|----------|-------------|----------|
| `GET` | `/api/profile` | — (JWT in header) | `{ age, height, weight, cycle_length, last_period }` |
| `PUT` | `/api/profile` | `{ age, height, weight, cycle_length, last_period }` | `{ success, message }` |

### 3. Daily Log Routes

| Method | Endpoint | Request Body | Response |
|--------|----------|-------------|----------|
| `POST` | `/api/daily-log` | `{ date, sleep, hydration, mood, nutrition, activity, notes }` | `{ success, message }` |
| `GET` | `/api/daily-log?date=YYYY-MM-DD` | — (JWT in header) | `{ log data }` |
| `GET` | `/api/daily-log/history?days=7` | — (JWT in header) | `[ array of logs ]` |

### 4. Cycle Routes

| Method | Endpoint | Request Body | Response |
|--------|----------|-------------|----------|
| `POST` | `/api/cycle` | `{ start_date, end_date, status, symptoms, flow, pain }` | `{ success, predicted_next, message }` |
| `GET` | `/api/cycle/history` | — (JWT in header) | `[ array of cycle logs ]` |

### 5. AI Insights Route

| Method | Endpoint | Request Body | Response |
|--------|----------|-------------|----------|
| `POST` | `/api/insights` | `{ summary_data }` | `{ insights: [...] }` |

---

## Required Dependencies

```txt
Flask==3.1.1
Flask-JWT-Extended==4.7.1
Flask-Bcrypt==1.0.1
Flask-CORS==5.0.1
pymongo==4.11.3
python-dotenv==1.1.0
google-generativeai==0.8.5
```

---

## Implementation Phases

### Phase 1 — Core Backend Setup
- [ ] Set up Flask app + config + CORS
- [ ] Connect to MongoDB
- [ ] Build auth routes (register/login with bcrypt + JWT)
- [ ] Test with existing frontend sign-in/sign-up pages

### Phase 2 — Data Routes
- [ ] Build health profile CRUD routes
- [ ] Build daily log CRUD routes
- [ ] Build cycle tracker CRUD routes
- [ ] Update frontend pages to make API calls (replace localStorage-only saves)

### Phase 3 — AI Integration
- [ ] Integrate Gemini AI for personalized insights
- [ ] Build the `/api/insights` endpoint
- [ ] Connect insight page's "Analyse" button to real API

### Phase 4 — Polish & Fixes
- [ ] Fix frontend bugs (password `.trim`, phone `id`, nav links)
- [ ] Add proper logout functionality
- [ ] Add error handling & loading states for API calls
- [ ] Consistent navigation across all pages

---

## Prerequisites Checklist

- [ ] Python 3.10+ installed
- [ ] MongoDB installed locally **or** MongoDB Atlas (cloud) account
- [ ] Gemini API key (from Google AI Studio)
- [ ] pip / virtualenv set up

---

> 🌸 Made with care for every woman on her PCOD journey.
