# Demo website (Next.js)

Separate Vercel project (Root Directory = `web`). See the repository README, section **Demo website**, for setup, deployment, environment variables, the white-label guide and the presenter-mode demo script.

| Route | View |
|---|---|
| `/` | Public website for the fictional client, with the floating AI assistant widget (voice + chat) |
| `/dashboard` | Business dashboard: calls, timeline, appointment, notifications, schedule, stats |
| `/present` | Website and live dashboard side by side, for sales calls |

```bash
cp .env.example .env.local   # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm install
npm run dev                  # http://localhost:3000
npm run typecheck && npm run build
```

- All client-specific content (company, phone, services, reviews, areas, colours, job value, agency name) comes from the API's `config/branding.yaml` and `config/company.yaml` via `GET /demo/branding`. No code changes for a new prospect.
- No secrets live here: the Retell API key and the demo access code are never bundled. The visitor types the access code (inside the widget or on the dashboard); it is kept in `sessionStorage` and sent as `X-Demo-Code`.
- Voice uses `retell-client-js-sdk` pinned to 3.0.2 (legacy `RetellWebClient`, started from a server-minted token).
- Images: original SVGs only; icons from Lucide (ISC); fonts Inter and Fraunces (OFL). See the main README.
