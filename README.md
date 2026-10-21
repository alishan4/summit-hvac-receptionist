# Summit Heating & Air - After-Hours AI Receptionist (demo)

An inbound-only AI phone receptionist for a fictional Denver HVAC company. It triages the issue, handles gas/CO safety emergencies, checks the service area, books a 2-hour arrival window on Google Calendar, texts a confirmation, and emails the owner a summary.

**Stack:** Retell AI (voice + function calling) - Twilio (number + SMS) - FastAPI / Pydantic v2 / SQLAlchemy (SQLite) - Google Calendar (service account) - SMTP email (Resend optional).

```
caller -> Twilio number -> Retell agent --(custom functions, signed)--> FastAPI /tools/*
                                        --(call_started/ended/analyzed)--> FastAPI /webhooks/retell
FastAPI -> Google Calendar (free/busy + events) | Twilio SMS | SMTP email | SQLite
```

## Project layout

```
api/index.py               Vercel serverless entrypoint (vercel.json rewrites all routes here)
config/company.yaml        all client-specific values (name, tz, ZIPs, hours, fee, owner, greeting)
prompts/agent_prompt.md    voice prompt, {{variables}} filled from company.yaml
app/                       FastAPI app (routers/, services/, models, schemas, security)
scripts/setup_retell_agent.py   create/update the Retell LLM + agent
scripts/init_db.py         one-off table creation (never runs at startup)
tests/                     pytest suite (no network, no credentials needed)
```

## White-labelling a new client

1. `cp config/company.yaml config/acme.yaml` and edit it (name, timezone, ZIPs, hours, fee, owner contacts, greeting).
2. Set `COMPANY_CONFIG_PATH=config/acme.yaml` in `.env`.
3. Adjust the prompt wording if needed (`prompts/agent_prompt.md`). Every `{{name}}` must exist in `company.yaml` (the renderer fails loudly if not).
4. Run `python scripts/setup_retell_agent.py`. Done: new agent, new calendar, new number.

Hours, slot length, lead time, how many slots to offer, and the dispatch fee are all in the YAML `scheduling` / `pricing` sections.

## Setup, step by step

### 0. Install
```bash
uv sync --python 3.12          # or: python3.12 -m venv .venv && .venv/bin/pip install -e . pytest
cp .env.example .env
.venv/bin/pytest               # should be all green before you touch any account
.venv/bin/python scripts/init_db.py   # creates tables (local SQLite file by default)
```
Tables are never created at app startup. Run `scripts/init_db.py` once per environment (and after schema changes).

### 1. Retell account
1. Sign up at retellai.com and create an **API key** (Dashboard -> API Keys). The key needs the **webhook badge**: Retell signs webhooks and function calls with it, and this app verifies them with the same key.
2. Put it in `.env` as `RETELL_API_KEY`.
3. Optional: pick a voice in the dashboard and set `RETELL_VOICE_ID`.

### 2. Twilio number -> Retell
1. In Twilio, buy a US local number (Denver 720/303 looks nice for the demo) with SMS capability.
2. Put `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and the number (E.164) as `TWILIO_FROM_NUMBER` in `.env`.
3. In Retell: **Phone Numbers -> Import** (Twilio / SIP trunk). Follow Retell's current import guide: it has you create an Elastic SIP trunk in Twilio and enter the number plus termination URI/credentials in Retell.
4. After step 5 below, set the imported number's **inbound agent** to the "Summit Heating & Air - After Hours" agent.

> US A2P 10DLC: sending SMS from a US local number to US phones generally requires registering a campaign in Twilio. Toll-free numbers need toll-free verification. Do this early, as approval can take days. Until approved, demo SMS may be filtered. Use `SMS_BACKEND=log` to rehearse without it.

### 3. Google Calendar service account
1. Google Cloud Console -> create a project -> enable **Google Calendar API**.
2. IAM -> Service Accounts -> create one -> Keys -> **Add key -> JSON**. Save it as `secrets/service-account.json` (git-ignored).
3. In Google Calendar, create a calendar named e.g. "Summit Technician Schedule". Settings -> **Share with specific people** -> add the service account's email (`...@...iam.gserviceaccount.com`) with **Make changes to events**.
4. Settings -> *Integrate calendar* -> copy the **Calendar ID** into `GOOGLE_CALENDAR_ID`.
5. Put the key path in `GOOGLE_SERVICE_ACCOUNT_FILE` (or paste raw JSON into `GOOGLE_SERVICE_ACCOUNT_JSON` for containers).

Availability = business hours from `company.yaml` minus anything already on this calendar. Add events there (e.g. "Tech lunch", existing jobs) to block time.

No credentials yet? `CALENDAR_BACKEND=fake` runs against an in-memory calendar (resets on restart).

### 4. Email (owner summaries and emergency alerts)
Default is **SMTP** (free): for Gmail use an app password with `smtp.gmail.com:587`. `EMAIL_BACKEND=resend` + `RESEND_API_KEY` is supported but optional. `EMAIL_BACKEND=log` just logs. Set the recipient under `owner.email` in the YAML.

### 5. Run locally with ngrok
```bash
.venv/bin/uvicorn app.main:app --reload --port 8000
ngrok http 8000                      # copy the https URL
```
Put that URL in `.env` as `PUBLIC_BASE_URL` (no trailing slash), restart uvicorn, then:
```bash
.venv/bin/python scripts/setup_retell_agent.py --dry-run   # inspect what will be sent
.venv/bin/python scripts/setup_retell_agent.py             # create (first run) or update in place
```
IDs are stored in `.retell_agent.json`. **Re-run the script whenever the ngrok URL, YAML, or prompt changes.** Then attach the agent to your number (step 2.4).

Quick checks: `curl localhost:8000/health` -> `{"status":"ok",...}`. In the Retell dashboard you can also use **Test Audio / Web Call** on the agent before calling the real number.

### 6. Make a test call
Call your Twilio number from your cell. Watch the uvicorn logs (JSON lines). Afterwards check the calendar, your SMS, the owner email, and the DB:
```bash
sqlite3 summit.db "select retell_call_id, outcome, urgency, duration from calls order by id desc limit 5;"
```

### 7. Docker
```bash
docker build -t summit-receptionist .
docker run -p 8000:8000 --env-file .env -v summit-data:/data \
  -v $PWD/secrets:/app/secrets:ro summit-receptionist
```
Use Postgres by setting `DATABASE_URL` to a `postgresql://...` URL (the `psycopg` driver is already included), and run `python scripts/init_db.py` once.

## Deploy to Vercel (free tier) with Neon Postgres

The app runs as one Python serverless function (`api/index.py`); `vercel.json` rewrites every route (`/health`, `/tools/*`, `/webhooks/retell`) to it. Dependencies come from `requirements.txt` (keep it in sync with `pyproject.toml`).

1. **Create a Neon project** at neon.tech (free plan is fine). Pick a region close to your Vercel region (default `iad1`, US East).
2. **Copy the pooled connection string**: Neon dashboard -> *Connect* -> toggle **Connection pooling** on. The host contains `-pooler`, e.g.
   `postgresql://user:pass@ep-xxx-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require`.
   The app keeps no connections between invocations (`NullPool`) and disables prepared statements, which PgBouncer's transaction mode needs. Do not use the non-pooled string for the running app.
3. **Create the tables** (one-off, from your laptop):
   ```bash
   DATABASE_URL='postgresql://...-pooler...?sslmode=require' .venv/bin/python scripts/init_db.py
   # -> ok - postgresql: tables = appointments, calls
   ```
4. **Import the repo in Vercel** (Add New -> Project -> pick this GitHub repo; framework preset "Other"). Or use the CLI: `npx vercel`.
5. **Set environment variables** (Project -> Settings -> Environment Variables, Production). Copy from `.env.example`; the ones that matter:
   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | the Neon **pooled** string |
   | `PUBLIC_BASE_URL` | your Vercel production URL, e.g. `https://summit-hvac-receptionist.vercel.app` (set after the first deploy) |
   | `RETELL_API_KEY`, `RETELL_VERIFY_SIGNATURE=true` | as before |
   | `CALENDAR_BACKEND=google`, `GOOGLE_CALENDAR_ID` | as before |
   | `GOOGLE_SERVICE_ACCOUNT_JSON` | the **whole key JSON** pasted as the value. There is no `secrets/` folder on Vercel, so leave `GOOGLE_SERVICE_ACCOUNT_FILE` empty |
   | `SMS_BACKEND=twilio`, `TWILIO_*` | as before |
   | `EMAIL_BACKEND`, `EMAIL_FROM`, `SMTP_*` (or `RESEND_API_KEY`) | as before |
6. **Redeploy** so the variables take effect (Deployments -> ... -> Redeploy, or `npx vercel --prod`). Check `curl https://<your-app>.vercel.app/health`.
7. **Point Retell at Vercel**: set `PUBLIC_BASE_URL` in your local `.env` to the Vercel URL, then
   ```bash
   .venv/bin/python scripts/setup_retell_agent.py   # updates the existing agent in place
   ```
   Tools and webhooks now call Vercel; ngrok is no longer needed. Re-run the script whenever the URL, YAML or prompt changes.

Serverless notes:
- **No filesystem writes at runtime.** Logs go to stdout (Vercel logs), the database is Postgres, credentials come from env vars. SQLite is refused on Vercel with a clear error.
- **Side effects run before the response on Vercel.** The booking SMS, emergency alert and summary email run inline there, because a serverless function can be frozen right after it responds and drop background work. This adds roughly a second to those calls. Elsewhere (local, Docker) they run after the response.
- **Limits.** `maxDuration` is 30 s. Retell's tool timeout is 15 s. A cold start adds about a second to the first call after idle time, so make one test call or hit `/health` before a live demo.
- Hobby (free) plans are for non-commercial use under Vercel's terms. Move a paying client to Pro.

## 5 test call scripts

Use the numbers below as the caller. Expected results are in italics.

**1. Normal booking.** "Hi, my furnace stopped working. It's 25 degrees out and I've got a baby at home." -> Name "Jamie Rivera" (spell it) -> "yes, this number's fine" -> "123 Main Street, zip 80203" -> "gas furnace, about 12 years old" -> pick the first window -> "yes, the fee's fine" -> *Agent states the fee before booking, books, confirms the day/window/address. Calendar event with all details, SMS received, `outcome=booked`, `urgency=urgent`, owner email.*

**2. Out of area.** "My AC isn't cooling." ... give address in Boulder, zip **80301**. -> *Agent apologizes, does not book, offers to take a message. `outcome=info_only` (or `callback` if you leave a message).*

**3. Emergency, gas smell.** "I smell gas near my furnace." (say it any time, even mid-booking) -> *Agent immediately tells you to leave, call 911 and the gas utility, does NOT book or ask more questions. Owner gets SMS + `[EMERGENCY]` email within seconds. `outcome=emergency`. Try then saying "ok, can you still book me?" -> it must refuse.*

**4. Wants a human.** "I'd like to talk to a real person about a quote for a new system." -> *Agent says it can't connect you now, takes name, number and message. `outcome=callback`, owner email contains the message under CALLBACK REQUESTED.*

**5. Hangs up mid-call.** Start a normal booking, give your name and address, hear the time slots, then hang up. -> *No appointment or calendar event. `outcome=abandoned`; owner still gets the summary email. (Hang up in the first 5 seconds -> also `abandoned`.)*

## Behaviour notes

- **Idempotent booking.** Key = hash(call id, slot start). Retries return the existing appointment with no second calendar event or SMS. The calendar event id is derived from the key, so a Google 409 is treated as already created. A UNIQUE index on `slot_start` is the final guard against two callers taking the same window. A calendar failure rolls the DB row back.
- **Signatures.** `/tools/*` and `/webhooks/retell` verify `X-Retell-Signature` (`v=<ms>,d=<HMAC-SHA256(body+ts, API key)>`, 5-minute window). Keep `RETELL_VERIFY_SIGNATURE=true` outside of curl experiments.
- **Emergencies.** `flag_emergency` sets the call to `emergency`, texts and emails the owner once (idempotent), and blocks bookings on that call. If the alert fails at tool time, the `call_ended` webhook retries it. Outcome never downgrades (emergency > booked > callback > info_only > abandoned).
- **Logging.** JSON logs carry call ids, outcomes, and masked numbers (`***1234`). No names, addresses, or transcripts. Transcripts go only to the DB and owner email.
- **Database.** `DATABASE_URL` selects Postgres (prod) or SQLite (local dev/tests). `TEST_DATABASE_URL=postgresql://... pytest` runs the suite against Postgres.
- **Single technician.** One calendar = one tech. For multiple techs, use one calendar per tech and change the unique constraint on `appointments`.
- **Dispatch timing.** Windows come from business hours + `min_lead_hours`; the agent never promises same-night arrival.

## Verify before going live

- Gas utility name/number in `company.yaml` (placeholder for the fictional client).
- Recording/AI-disclosure rules in your client's state. The greeting discloses AI. Add a recording notice if you record calls.
- Twilio A2P/toll-free registration for SMS.
- Retell field names evolve. If `setup_retell_agent.py` returns a 4xx, the response body is printed. Adjust `build_payloads()` / `app/services/retell_tools.py`.

## Tests
```bash
.venv/bin/pytest -v
```
Covers slot logic, ZIP check, booking idempotency and race backstops, emergency path, webhook lifecycle, signature verification, prompt rendering, and the setup script dry run.
