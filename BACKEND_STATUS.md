# Backend Status

Last verified: 2026-06-19

## Current readiness

Backend MVP readiness: about 93%.

The API is ready for frontend/mobile integration for the main flows:

- JWT auth: register, login, refresh, logout.
- Current user profile and goals.
- Exercise catalog with system and user exercises.
- Training routines, days, and planned exercises.
- Workout start, active workout, sets, finish/cancel, history, personal records.
- Food catalog, barcode lookup, meals, meal items, day totals, targets, progress.
- AI food photo recognition with draft/edit/confirm flow.
- Privacy-first AI photo handling: uploaded files are deleted after recognition processing.
- Dashboard summary and trends.
- Healthcheck, request IDs, consistent JSON errors.
- Swagger/OpenAPI schema with request/response bodies, query params, path params, and stable operation IDs.
- Scoped rate limits for auth and AI photo upload.
- CORS support for configured frontend origins.
- Docker Compose with PostgreSQL backend service.

## Verification commands

Run from `apps/backend`:

```bash
python manage.py check
python manage.py spectacular --file /tmp/fittrack-schema.yaml --validate --fail-on-warn
pytest -q
```

Current expected test result:

```text
225 passed
```

The remaining warnings are from `drf_spectacular` on Python 3.14 deprecations, not project code.

## Local and Docker env

Docker Compose uses the root `.env` file:

```bash
cp .env.example .env
docker compose up -d --build
```

Local Django commands use `apps/backend/.env`:

```bash
cp apps/backend/.env.example apps/backend/.env
cd apps/backend
python manage.py migrate
python manage.py runserver
```

PostgreSQL from the host:

```env
DATABASE_URL=postgres://fittrack:fittrack_password@localhost:5432/fittrack
```

PostgreSQL from Docker backend:

```env
DATABASE_URL=postgres://fittrack:fittrack_password@db:5432/fittrack
```

## AI photo recognition

Disabled mode:

```env
NUTRITION_AI_PHOTO_PROVIDER=disabled
```

Gemini mode:

```env
NUTRITION_AI_PHOTO_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.5-flash
NUTRITION_AI_PHOTO_HTTP_TIMEOUT_SECONDS=60
```

## Rate limits

```env
DRF_AUTH_THROTTLE_RATE=30/min
DRF_AI_PHOTO_UPLOAD_THROTTLE_RATE=10/min
```

Throttled responses use the standard error envelope with code `THROTTLED`.

## Frontend CORS

```env
DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
DJANGO_CORS_ALLOW_CREDENTIALS=false
```

Upload endpoint:

```http
POST /api/v1/nutrition/photo-recognitions/upload
```

Confirm endpoint:

```http
POST /api/v1/nutrition/photo-recognitions/{recognition_id}/confirm
```

## API docs

```text
Swagger UI: /api/v1/docs/
OpenAPI schema: /api/v1/schema/
```

If Swagger shows old operation IDs or missing response bodies, rebuild/restart the backend:

```bash
docker compose up -d --build backend
```

Then hard refresh the browser.

## Remaining backend work before frontend

- Add frontend-oriented example payloads for the most common screens.
- Add pagination to workout/routine lists if frontend needs infinite scroll.
- Decide whether anonymous exercise catalog access is intended for production.
- Add deployment settings for HTTPS, secure cookies if browser auth appears, and stricter `DJANGO_ALLOWED_HOSTS`.
- Add CI command once repository hosting is ready.

## Production hardening later

- Rotate `DJANGO_SECRET_KEY` outside git and never commit real `.env`.
- Use a managed PostgreSQL backup policy.
- Configure structured log collection.
- Monitor AI provider timeouts and error rates.
- Add API version deprecation policy before changing response contracts.
