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
web/                       Next.js demo website (separate Vercel project)
config/branding.yaml       white-label branding + public-site content + dashboard settings (+ config/branding/logo.svg)
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

The app runs as one Python serverless function using Vercel's zero-config FastAPI support: `[tool.vercel] entrypoint = "app.main:app"` in `pyproject.toml`, and `vercel.json` only sets `maxDuration` and bundles `config/` + `prompts/`. Vercel routes every path (`/health`, `/tools/*`, `/webhooks/retell`) to the app **unchanged**. Do not add `rewrites`/`routes` to an `api/` file: the function then receives the rewritten path (e.g. `/api/index`) and every route returns FastAPI's `{"detail":"Not Found"}`. Dependencies come from `requirements.txt` (keep it in sync with `pyproject.toml`).

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

## Demo website (for sales calls and Loom recordings)

`/web` is a Next.js (App Router, TypeScript, Tailwind) project with three views of the same fictional client, so on a sales call you can show both sides of the workflow:

| Route | Who it's for | What it is |
|---|---|---|
| **`/`** | the homeowner | A realistic public site for "Summit Heating & Air" (hero, services, why-us, reviews, service-area ZIP checker, about, CTA, footer). A floating **assistant widget** (voice call or text chat) sits on every page, and every "Talk to us now" / "Book service" button opens it. A time-aware banner (company timezone) invites after-hours visitors to book right now. The access code is entered **inside the widget**, so the site itself is public. |
| **`/dashboard`** | the business owner | A SaaS-style dashboard: today's calls list (live badge), each call's timeline, AI summary, appointment details, SMS + owner-email previews, day calendar, and stats including **estimated revenue protected** (booked jobs x average job value). It follows the live call automatically. |
| **`/present`** | you, on a call | Split screen: the website (~60%) beside the live dashboard (~40%). Scenario chips with copy and "send to chat" buttons, plus Reset. Below the `lg` breakpoint the two halves become "Homeowner view / Business view" tabs. |

It talks to this API's `/demo/*` endpoints; the Retell API key never reaches the browser.

```
browser (/web) --X-Demo-Code--> API /demo/*  --Retell API key--> Retell (web call token / chat)
   |  voice audio goes browser <-> Retell directly, using a one-time token minted by the API
   '-- dashboard polls /demo/calls and /demo/calls/{id}/events -> live timeline, appointment, previews
   '-- /present embeds "/" in an iframe; the widget tells the dashboard which call is live (postMessage)
```

### How the Retell pieces fit (verified against Retell's docs and SDK packages)
- **Voice:** the API calls `POST /v3/create-web-call` (the v2 endpoint was deprecated on 2026-10-18) and returns the one-time `access_token`. The browser starts audio with the SDK's `RetellWebClient.startCall({accessToken, ...})`, pinned to `retell-client-js-sdk@3.0.2`. SDK 3.x's newer `RetellClient.createWebCall` needs a Retell *public key* in the browser and would bypass the access code, so it is not used. `RetellWebClient` is deprecated and removed in SDK 4.0, so keep the pin.
- **Text chat:** Retell has a chat API (`/create-chat`, `/create-chat-completion`). `scripts/setup_retell_agent.py` now also creates a **chat agent that reuses the same Retell LLM**, so the prompt and the six tools are identical to voice.
- **Live captions:** Retell only exposes a call's transcript after it ends, and its live-transcript stream needs an API key in the browser, which this project refuses to do. The site therefore shows captions from the SDK's `update` events when the platform emits them, and otherwise falls back to the conversation-so-far that Retell sends to our tools on every function call (it refreshes each time the agent checks a system). The full transcript lands when the call ends.
- **No caller ID:** web and chat sessions have no phone number. The prompt asks for one, and `book_appointment` / `request_callback` refuse to proceed without it.

### Protecting your Retell credits
| Guard | Where |
|---|---|
| **Access code** (`DEMO_ACCESS_CODE`). No code = nothing calls Retell. Unset = `/demo` disabled | every `/demo/*` route except branding |
| **Rate limit**: 5 voice calls/hour and 10 chats/hour per IP (DB-backed, so it works on serverless) | `/demo/web-call`, `/demo/chat` |
| **Daily ceiling**: 30 paid sessions per 24h across all visitors | same |
| **4-minute cap** per call (`agent_override.max_call_duration_ms`; phone calls on the same agent are unaffected) and per chat; 30 messages per chat | server-side |
| **Brute-force guard**: 10 wrong codes/hour per IP locks that IP out | access check |
| Mic permission is requested *before* a call is created, so a denied prompt costs nothing | browser |
| Reset keeps the rate-limit ledger, so it can't be used to dodge limits | `/demo/reset` |

### Run it locally
```bash
# 1) API (.env needs DEMO_ACCESS_CODE, DEMO_ALLOWED_ORIGINS=http://localhost:3000, RETELL_AGENT_ID, RETELL_CHAT_AGENT_ID)
.venv/bin/python scripts/setup_retell_agent.py      # recreates/updates voice + chat agents, prints the two agent ids
.venv/bin/python scripts/init_db.py                 # also creates the new call_events / demo_hits tables
.venv/bin/uvicorn app.main:app --port 8000
# 2) site
cd web && cp .env.example .env.local                # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm install && npm run dev                          # http://localhost:3000
```
Voice needs the API reachable by Retell for the tools/webhooks (use ngrok as in the main setup and set `PUBLIC_BASE_URL`); the browser itself can use `http://localhost:8000`. Browsers allow the microphone on `localhost` and `https` only.

### Deploy the site (second Vercel project)
1. Vercel -> Add New -> Project -> import this same repo -> **Root Directory: `web`** (framework: Next.js is auto-detected).
2. Environment variable: `NEXT_PUBLIC_API_BASE_URL` = your API's URL (e.g. `https://summit-hvac-receptionist.vercel.app`). It is public by design. Nothing secret lives in this project.
3. Deploy, then copy the site's URL (e.g. `https://summit-demo.vercel.app`).
4. On the **API** project add `DEMO_ALLOWED_ORIGINS=https://summit-demo.vercel.app` (CORS: only this origin may call `/demo` from a browser), plus the variables below, and redeploy it.
5. Run `python scripts/init_db.py` once against the Neon database (adds `call_events` and `demo_hits`; existing tables are untouched).
6. Re-run `python scripts/setup_retell_agent.py` (new prompt + chat agent) and copy the printed `RETELL_AGENT_ID` / `RETELL_CHAT_AGENT_ID` into the API project's env vars, then redeploy the API.

**Two projects, one repo:** the API project (Root Directory = repo root) keeps `web/` out of its function bundle with `functions.excludeFiles: "web/**"` in the root `vercel.json`. Do **not** put `web` in the root `.vercelignore`: that file applies to the whole upload, including the web project, and deleting `web/package.json` makes its build fail with `NEXT_NO_VERSION`. `web/.vercelignore` exists so the web project never depends on the root file. A test (`test_two_vercel_projects_share_one_repo_safely`) guards this.

### Environment variables
| Project | Variable | Purpose |
|---|---|---|
| **web** | `NEXT_PUBLIC_API_BASE_URL` | URL of the API (public) |
| **API** | `DEMO_ACCESS_CODE` | code visitors must enter. **Unset disables `/demo`** |
| API | `DEMO_ALLOWED_ORIGINS` | comma-separated site origin(s) for CORS |
| API | `RETELL_AGENT_ID`, `RETELL_CHAT_AGENT_ID` | printed by `setup_retell_agent.py` |
| API | `DEMO_MAX_CALL_SECONDS` (240), `DEMO_WEB_CALLS_PER_HOUR` (5), `DEMO_CHATS_PER_HOUR` (10), `DEMO_MAX_CALLS_PER_DAY` (30), `DEMO_MAX_CHAT_MESSAGES` (30), `DEMO_BAD_CODES_PER_HOUR` (10) | credit protection, defaults shown |
| API | `BRANDING_CONFIG_PATH` | default `config/branding.yaml` |

### Make a new client demo in under 10 minutes
Nothing client-specific is hard-coded in `/web`. The site reads everything from the API, which reads two YAML files:

| What | Where |
|---|---|
| Company name, timezone, **service-area ZIPs**, **business hours** (drive the after-hours banner), dispatch fee, greeting, owner contacts | `config/company.yaml` |
| Agency name + "Powered by" toggle, **accent colour**, tagline, badge, logo, scenario scripts | `config/branding.yaml` |
| **Public-site content**: phone, address, hours text, hero headline/subline, trust numbers (years, rating, review count), services, why-us points, reviews, city names, about copy, CTA, footer disclaimer | `config/branding.yaml` -> `site:` |
| **Average job value** for the revenue-protected tile | `config/branding.yaml` -> `dashboard.average_job_value` |

Steps:
1. `cp config/company.yaml config/acme.yaml`, edit it, set `COMPANY_CONFIG_PATH=config/acme.yaml`.
2. `cp config/branding.yaml config/acme-branding.yaml`, edit the values above, drop the client's logo in `config/branding/` (svg/png/jpg/webp) and point `logo_path` at it, set `BRANDING_CONFIG_PATH=config/acme-branding.yaml`.
3. Commit, push (the API redeploys) and run `python scripts/setup_retell_agent.py` so the agents get the new prompt. Update the agent id env vars if they changed.
4. Reload the site. It re-skins itself, **with no change or rebuild of the web project**. Copy placeholders `{dispatch_fee}`, `{company}` and `{phone}` work inside `why_choose` text.

Notes:
- **Accent colour must keep 4.5:1 contrast with white** (white text sits on it). The API refuses to start with a colour that fails, and says how to fix it.
- Service/why-us **icon names**: `snowflake flame waves wind wrench thermometer home shield-check clock calendar-check badge-dollar-sign siren leaf star users sparkles`. Unknown names fall back to a wrench.
- Keep reviews clearly fictional for a fictional client, and keep the footer `disclaimer`.

### Images and credits
No photos and no third-party artwork are used. The hero scene, logo and favicon are original SVGs created for this project (`web/src/components/site/HeroIllustration.tsx`, `config/branding/logo.svg`, `web/src/app/icon.svg`), and avatars are initials. UI icons come from [Lucide](https://lucide.dev) (ISC licence), and the fonts are Inter and Fraunces from Google Fonts (SIL Open Font Licence), loaded with `next/font`. All names, phone numbers (555-01xx), the address and the reviews are fictional. Nothing depicts a real company.

### Accessibility
Audited with axe-core (WCAG 2.1 AA + best practices) on the site, the widget (locked, chat, booked), the dashboard (empty and populated) and presenter mode: **0 violations**. Landmarks and a skip link are in place; the widget is a labelled dialog that takes focus on open, returns it on close, and closes with Esc; scrollable logs are keyboard-focusable; `prefers-reduced-motion` is respected.

### Demo script (presenter mode, about 5 minutes)
Open **`/present`** on the screen you share, enter the access code once (it unlocks both halves), and press **Reset demo** so the dashboard starts empty.

1. **Frame it (20 s).** "This left side is your client's website, what their customer sees. The right side is what the business sees. It's 9 pm and a customer's AC just died. Normally that's voicemail." Point at the after-hours banner and the "Need help? We answer 24/7" widget.
2. **Scenario 1: urgent booking (2 min).** Click the **AC broken + elderly parent** chip: the script appears in a bar under the top. Click the widget, choose **Call us**, **Start call**, and read the script naturally (or use the chip's chat button to drop it into the chat). Point at the **Business view** as it fills in:
   - **Today's calls**: the new call appears instantly with a **Live** badge.
   - **Live activity**: service area checked, slots found, booked. Each step appears as the AI does it.
   - The AI **states the $89 fee and waits for a yes** before booking.
   - **Outcome**: customer, address, issue, the **Urgent** badge (elderly parent), arrival window, "Added to calendar".
   - **Notifications**: the customer's confirmation text, and the owner's email (Draft until the call ends, then final with the AI summary).
   - **Stats**: calls and bookings tick up, and **revenue protected** grows by the average job value. "That's a job that would have gone to a competitor."
   - Back in the widget the homeowner sees the confirmation card: "You're booked: Thu 10-12 PM".
3. **Scenario 2: gas smell (1 min).** Click the **Gas smell** chip, start a new chat and send it. Point out: the AI tells them to leave and call 911 and the gas utility, **refuses to book**, and the dashboard shows a red **Emergency flagged**, **Owner alerted immediately**, and the **Owner alert** tab with the instant SMS and email. "The owner knows within seconds, at 2 am."
4. **Scenario 3: outside the area (30 s, optional).** Polite decline, nothing booked. Also try the **ZIP checker** on the site (80203 yes, 80301 no).
5. **Close (30 s).** Open **`/dashboard`** in a second tab for the full-width view. "Same system answers your clients' after-hours line. A new client is a config file, not a project." Press **Reset demo** so the next demo starts clean.

Tips: on a noisy line use the widget's **Chat** (or a chip's chat button): the business view behaves identically. The widget keeps a live call going if you minimise it, so you can scroll the site while the AI talks.

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
