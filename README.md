# ⚖️ Legal Doc Generator

Instant legal documents for $5-15 — no lawyer needed.

## Doc Types
- NDA ($5.99)
- Freelance Contract ($7.99)
- Privacy Policy ($9.99)
- Terms of Service ($9.99)
- LLC Operating Agreement ($14.99)

## Deploy
1. Fork this repo
2. Connect to [Render](https://render.com) as a Web Service
3. Set env vars: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `BASE_URL`
4. Deploy — demo mode works without Stripe keys

## Endpoints
- `GET /` — Landing page
- `POST /create-checkout` — Start checkout
- `GET /success` — Document delivery
- `GET /order/{id}/download` — Download .txt
- `GET /health` — Health check
