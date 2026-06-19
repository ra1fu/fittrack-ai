# FitTrack AI

Backend status and remaining checklist: [BACKEND_STATUS.md](BACKEND_STATUS.md)

## Local PostgreSQL with Docker

Create a root Docker Compose env file:

```bash
cp .env.example .env
```

Start PostgreSQL:

```bash
docker compose up -d db
```

Check container health:

```bash
docker compose ps
```

Create a backend env file for local `python manage.py` commands:

```bash
cp apps/backend/.env.example apps/backend/.env
```

For local PostgreSQL, set this in `apps/backend/.env`:

```env
DATABASE_URL=postgres://fittrack:fittrack_password@localhost:5432/fittrack
```

Run migrations and seed catalogs:

```bash
cd apps/backend
python manage.py migrate
python manage.py seed_exercise_catalogs
python manage.py seed_food_catalog
```

Run backend:

```bash
python manage.py runserver
```

Run tests with the default SQLite fallback:

```bash
pytest -q
```

Run tests against PostgreSQL explicitly:

```bash
TEST_DATABASE_URL=postgres://fittrack:fittrack_password@localhost:5432/fittrack pytest -q
```

## Full App With Docker

Create the root Docker Compose env file if it does not exist yet:

```bash
cp .env.example .env
```

Start PostgreSQL, backend, and frontend:

```bash
docker compose up -d --build
```

Optional automatic startup tasks:

```env
DJANGO_RUN_MIGRATIONS=true
DJANGO_SEED_CATALOGS=true
```

Rate limits:

```env
DRF_AUTH_THROTTLE_RATE=30/min
DRF_AI_PHOTO_UPLOAD_THROTTLE_RATE=10/min
```

Frontend CORS origins:

```env
DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
DJANGO_CORS_ALLOW_CREDENTIALS=false
VITE_API_URL=http://127.0.0.1:8000/api/v1
```

AI photo recognition with Gemini:

```env
NUTRITION_AI_PHOTO_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.5-flash
NUTRITION_AI_PHOTO_HTTP_TIMEOUT_SECONDS=60
```

AI photo recognition disabled:

```env
NUTRITION_AI_PHOTO_PROVIDER=disabled
```

Run migrations inside the backend container:

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_exercise_catalogs
docker compose exec backend python manage.py seed_food_catalog
```

Backend URL:

```text
http://127.0.0.1:8000
```

Frontend URL:

```text
http://127.0.0.1:5173
http://localhost:5173
```

Check backend health:

```bash
docker compose ps
curl http://127.0.0.1:8000/api/v1/health/
```

Check frontend health:

```bash
docker compose ps
curl http://127.0.0.1:5173
```

API docs:

```text
Swagger UI: http://127.0.0.1:8000/api/v1/docs/
OpenAPI schema: http://127.0.0.1:8000/api/v1/schema/
```

DataGrip connection:

```text
Host: localhost
Port: 5432
User: fittrack
Password: fittrack_password
Database: fittrack
```

## Frontend Local Commands

Install frontend dependencies:

```bash
cd apps/frontend
npm install
```

Run the frontend locally without Docker:

```bash
npm run dev
```

Local frontend URL:

```text
http://127.0.0.1:5173
http://localhost:5173
```

Frontend checks:

```bash
npm run lint
npm run test
npm run build
npm run e2e
```

Playwright browsers are required once before `npm run e2e`:

```bash
npx playwright install chromium
```

Manual smoke test:

1. Open `http://127.0.0.1:5173`.
2. Register a user with email, password, terms, and privacy checkboxes.
3. You should land on `/dashboard`.
4. Open `http://127.0.0.1:8000/api/v1/docs/` to inspect backend endpoints.
5. Use the app navigation for Nutrition, Photo AI, Exercises, Routines, Workouts, Records, and Profile.

## API quickstart

Set the base URL once:

```bash
export API_URL=http://127.0.0.1:8000/api/v1
```

Register a user:

```bash
curl -X POST "$API_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "strong-password-123",
    "accepted_terms": true,
    "accepted_privacy": true
  }'
```

Login and store tokens:

```bash
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "strong-password-123"
  }')

ACCESS_TOKEN=$(printf "%s" "$LOGIN_RESPONSE" | python -c 'import json,sys; print(json.load(sys.stdin)["data"]["access"])')
REFRESH_TOKEN=$(printf "%s" "$LOGIN_RESPONSE" | python -c 'import json,sys; print(json.load(sys.stdin)["data"]["refresh"])')
```

Call an authenticated endpoint:

```bash
curl "$API_URL/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Refresh an access token:

```bash
curl -X POST "$API_URL/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refresh\":\"$REFRESH_TOKEN\"}"
```

Logout:

```bash
curl -X POST "$API_URL/auth/logout" \
  -H "Content-Type: application/json" \
  -d "{\"refresh\":\"$REFRESH_TOKEN\"}"
```

## Nutrition flow

Create a food:

```bash
curl -X POST "$API_URL/foods" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Rice",
    "brand": "Local",
    "calories_per_100g": "130.00",
    "protein_per_100g": "2.70",
    "fat_per_100g": "0.30",
    "carbs_per_100g": "28.00"
  }'
```

Search foods:

```bash
curl "$API_URL/foods?search=rice&limit=20&offset=0" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Create a meal:

```bash
curl -X POST "$API_URL/meals" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "meal_date": "2026-06-19",
    "meal_type": "breakfast"
  }'
```

Check nutrition day:

```bash
curl "$API_URL/nutrition/days/2026-06-19" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Upload a meal photo for AI recognition:

```bash
curl -X POST "$API_URL/nutrition/photo-recognitions/upload" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "image=@/home/rauan/Pictures/meal.jpg;type=image/jpeg"
```

Confirm a draft recognition into a meal:

```bash
curl -X POST "$API_URL/nutrition/photo-recognitions/<recognition_id>/confirm" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "meal_date": "2026-06-19",
    "meal_type": "lunch"
  }'
```

## Workout flow

List visible exercises:

```bash
curl "$API_URL/exercises?search=bench&tracking_type=weight_reps" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Start a workout:

```bash
curl -X POST "$API_URL/workouts" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Push day",
    "local_device_id": "00000000-0000-4000-8000-000000000001"
  }'
```

Get active workout:

```bash
curl "$API_URL/workouts/active" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Finish a workout:

```bash
curl -X POST "$API_URL/workouts/<workout_id>/finish" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Dashboard summary:

```bash
curl "$API_URL/dashboard/summary?date=2026-06-19" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
