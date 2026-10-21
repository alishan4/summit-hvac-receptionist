# Demo website (Next.js)

Separate Vercel project (Root Directory = `web`). See the repository README, section **Demo website**, for setup, deployment, environment variables and the demo script.

```bash
cp .env.example .env.local   # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm install
npm run dev                  # http://localhost:3000
npm run typecheck && npm run build
```

- Branding (logo, accent colour, texts, scenario cards) comes from the API's `config/branding.yaml` via `GET /demo/branding`.
- No secrets live here: the Retell API key and the demo access code are never bundled. The visitor types the access code, which is kept in `sessionStorage` and sent as `X-Demo-Code`.
- Voice uses `retell-client-js-sdk` pinned to 3.0.2 (legacy `RetellWebClient`, started from a server-minted token).
