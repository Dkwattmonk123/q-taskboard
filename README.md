# TaskBoard — Project Management App

A fullstack project management app for managing projects, tasks, and team members.

**Tech Stack:** React 18 + Vite + TypeScript (frontend) · Django 5 + Django REST Framework + SimpleJWT (backend) · PostgreSQL 16

## Quick Setup (Docker — Recommended)

```bash
# Clone and enter the repo
git clone <repo-url> && cd q-taskboard

# Start all services
docker-compose up --build

# In a separate terminal, run migrations and seed
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py seed

# Run the test suites
docker-compose exec backend python -m pytest          # Django tests
docker-compose exec frontend npm test                 # React tests

# The app is now running at http://localhost:3000
# Backend API at http://localhost:8000
```

## Manual Setup (without Docker)

Requires: Python 3.12+, Node.js 20+, PostgreSQL 15+

```bash
chmod +x bin/setup
./bin/setup

# Or manually:

# Backend
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env   # edit POSTGRES_* if your local setup differs
python manage.py migrate
python manage.py seed
python -m pytest

# Frontend
cd ../frontend
npm install
npm test
npm run dev
```

## AI Tool Conversation Tracking

**This repository is configured to automatically capture your AI coding tool conversation history with each git commit.** This includes conversations from Claude Code, Cursor, Aider, Continue.dev, Cody, Cline, and Windsurf.

This is part of the Ajackus evaluation process. We evaluate how you collaborate with AI tools — your prompting strategy, how you break down problems, and how you review AI suggestions. The captured conversations help us understand your workflow.

**How it works:**
- A pre-commit git hook runs automatically before each commit
- It copies conversation files from AI tool directories (e.g., `.claude/`, `.cursor/`) into `.ai-conversations/`
- These files are staged and included in your commit
- You don't need to do anything — it happens automatically

**What's captured:** Only AI tool conversation logs stored in the project directory. No system files, browsing history, or anything outside this repository.

**If you prefer a tool that doesn't store local conversations** (like browser-based ChatGPT), the screen recording will capture your interactions instead. No additional action needed from you.

## Seed Data

All user passwords are: `password123`

| Email | Role |
|-------|------|
| meera@taskboard.dev | admin on Q3 Launch & Internal Tools, member on Onboarding |
| arjun@taskboard.dev | admin on Onboarding, member on Q3 Launch |
| kavya@example.com | member on Q3 Launch |
| dev@example.com | viewer on Q3 Launch |
| lina@example.com | member on Onboarding |

## Authentication

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"meera@taskboard.dev","password":"password123"}'

# Use the returned token
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/projects
```

## API Endpoints

### Auth
- `POST /api/auth/register` — Create account
- `POST /api/auth/login` — Sign in, get JWT
- `GET /api/users/me` — Current user (authenticated)

### Projects
- `GET /api/projects` — List projects you're a member of (authenticated)
- `POST /api/projects` — Create a project (authenticated; creator becomes admin)
- `GET /api/projects/:id` — Project detail with tasks and members (authenticated)
- `PATCH /api/projects/:id` — Update project (admin only)
- `DELETE /api/projects/:id` — Delete project (admin only)

### Tasks
- `GET /api/projects/:id/tasks` — List tasks in a project; supports `?q=` search (authenticated)
- `POST /api/projects/:id/tasks` — Create a task (admin or member)
- `PATCH /api/tasks/:id` — Update a task (authenticated)
- `DELETE /api/tasks/:id` — Delete a task (admin or member)

### Export
- `POST /api/projects/:id/export` — Export tasks to Airtable (admin or member)

## Airtable Export (Part 3c)

Set these in your `.env` before running the export:

```
AIRTABLE_API_KEY=your_personal_access_token
AIRTABLE_BASE_ID=appXXXXXXXXXXXXXX
AIRTABLE_TABLE_NAME=Tasks
```

The backend uses `pyairtable` for real API calls. `backend/projects/airtable_mock.py` is a test double — use it in unit tests, not in production code.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite 5, TypeScript 5 (strict) |
| Routing | React Router 6 |
| Data fetching | TanStack Query 5 |
| Styling | Tailwind CSS 3 |
| Frontend tests | Vitest 2 + Testing Library |
| Backend | Django 5, Django REST Framework 3 |
| Auth | djangorestframework-simplejwt (JWT, 30-day tokens) |
| ORM | Django ORM |
| Database | PostgreSQL 16 |
| Backend tests | pytest-django |
| Container | Docker + docker-compose |