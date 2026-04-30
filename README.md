# EMS
Employee management system Django backend api

## AI task summaries (Groq)

### Environment

Set server-side env var in `.env`:

- `GROQ_API_KEY=...`

### Endpoints

- `POST /api/ai/summary/run/` body `{"type":"intern"|"employee"|"teamlead"|"md"}`
- `GET /api/ai/summary/latest/?type=intern`

Both endpoints require authentication (use your existing auth/session/JWT setup).
