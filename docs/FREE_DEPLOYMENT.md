# RealDeal AI -- Free Deployment Guide ($0/month)

This guide shows how to deploy RealDeal AI with **zero monthly cost** using free tiers of modern cloud services.

---

## Free Hosting Stack

| Service | Provider | Free Tier | Limit |
|---------|----------|-----------|-------|
| Frontend | Vercel | Free | Unlimited bandwidth (personal) |
| Backend | Render | Free | 750 hrs/month (sleeps after 15 min) |
| Database | Neon PostgreSQL | Free | 500 MB, 0.25 vCPU |
| Redis/Cache | Upstash | Free | 10K commands/day, 256 MB |
| Email | SendGrid | Free | 100 emails/day |
| Email (alt) | Gmail SMTP | Free | Unlimited (personal) |
| Maps | OpenStreetMap + Leaflet | Free | Unlimited, no API key |
| AI Analysis | Template-based | Free | No LLM needed |
| AI Text (opt) | Ollama local | Free | Runs on your machine |
| CI/CD | GitHub Actions | Free | 2,000 min/month |
| Domain | Vercel/Render subdomain | Free | yourapp.vercel.app |
| Error Tracking | Sentry | Free | 5K errors/month |

**Total monthly cost: $0**

---

## Step-by-Step Deployment

### 1. Fork the Repository

```bash
# Fork on GitHub, then clone
git clone https://github.com/YOUR_USERNAME/realdeal-ai.git
cd realdeal-ai
```

### 2. Create Neon Database (FREE)

1. Go to [neon.tech](https://neon.tech) and sign up (GitHub login works)
2. Click "Create Project"
3. Choose the **Free** tier (500 MB, 0.25 vCPU)
4. Select your region (US East recommended)
5. Copy the connection string -- it looks like:
   ```
   postgresql://user:password@ep-xxxx-xxxx.us-east-2.aws.neon.tech/realdeal?sslmode=require
   ```
6. Save this as your `DATABASE_URL`

### 3. Create Upstash Redis (FREE)

1. Go to [upstash.com](https://upstash.com) and sign up
2. Click "Create Database"
3. Choose the **Free** tier (10K commands/day, 256 MB)
4. Select your region
5. Copy the Redis URL -- it looks like:
   ```
   rediss://default:xxxx@yyyy.upstash.io:6379
   ```
6. Save this as your `REDIS_URL`

### 4. Deploy Frontend to Vercel (FREE)

1. Go to [vercel.com](https://vercel.com) and sign up with GitHub
2. Click "Import Project" and select your forked repo
3. Set the root directory to `frontend`
4. Set framework preset to "Vite"
5. Add environment variable:
   - `VITE_API_URL` = your Render backend URL (from step 5)
6. Click "Deploy"
7. Your frontend is live at `https://your-app.vercel.app`

### 5. Deploy Backend to Render (FREE)

1. Go to [render.com](https://render.com) and sign up with GitHub
2. Click "New Web Service"
3. Connect your forked repo
4. Configure:
   - **Root Directory:** `backend`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Free
5. Add environment variables:
   ```
   DATABASE_URL=<your Neon connection string>
   REDIS_URL=<your Upstash Redis URL>
   JWT_SECRET=<generate a random 64-char string>
   CORS_ORIGINS=https://your-app.vercel.app
   ENVIRONMENT=production
   ```
6. Click "Create Web Service"
7. Your backend is live at `https://your-app.onrender.com`

### 6. Run Database Migrations

```bash
# Option A: From Render shell
# Go to Render dashboard -> your service -> Shell tab
alembic upgrade head

# Option B: Locally with Neon URL
DATABASE_URL="your-neon-url" alembic upgrade head
```

### 7. Set Up Email (Optional)

**Option A: SendGrid (100 emails/day free)**
1. Sign up at [sendgrid.com](https://sendgrid.com)
2. Create an API key (Settings -> API Keys -> Create)
3. Add `SENDGRID_API_KEY` to your Render env vars

**Option B: Gmail SMTP (free, unlimited)**
1. Enable 2-Factor Authentication on your Gmail
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Create an App Password for "Mail"
4. Add to Render env vars:
   ```
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your.email@gmail.com
   SMTP_PASSWORD=your_app_password
   ```

### 8. (Optional) Set Up Ollama for AI Summaries

The app works perfectly without any LLM. All analysis is math-based and summaries
are generated from templates using actual calculated metrics.

If you want richer AI-generated text:

```bash
# Local development only (Ollama runs on your machine)
docker compose --profile with-ollama up -d ollama
docker exec realdeal-ollama ollama pull llama3

# Add to .env:
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

### 9. Done!

Your app is now running at `https://your-app.vercel.app` with a total cost of **$0/month**.

---

## Cost Comparison

| Component | Free Tier | Pro ($50-100/mo) | Production ($300+/mo) |
|-----------|-----------|-------------------|----------------------|
| **Frontend** | Vercel Free | Vercel Pro ($20/mo) | Vercel Enterprise |
| **Backend** | Render Free | Render Starter ($7/mo) | AWS ECS ($50+/mo) |
| **Database** | Neon Free (500MB) | Neon Launch ($19/mo, 10GB) | RDS ($100+/mo) |
| **Redis** | Upstash Free (256MB) | Upstash Pro ($10/mo) | ElastiCache ($50+/mo) |
| **Email** | SendGrid Free (100/day) | SendGrid Essentials ($20/mo) | SES ($0.10/1K) |
| **Maps** | Leaflet+OSM (free) | Leaflet+OSM (free) | Mapbox ($50+/mo) |
| **AI** | Templates (free) | Ollama local (free) | Claude API ($50+/mo) |
| **CI/CD** | GitHub Actions Free | GitHub Actions Free | GitHub Actions ($4/user) |
| **Monitoring** | Sentry Free | Sentry Team ($26/mo) | Datadog ($100+/mo) |
| **Domain** | Free subdomain | Custom domain ($12/yr) | Custom domain ($12/yr) |
| | | | |
| **TOTAL** | **$0/month** | **~$76/month** | **~$400+/month** |

---

## Free Tier Limitations

### Render Free Tier
- **Cold starts:** Service sleeps after 15 minutes of inactivity. First request after sleep takes ~30 seconds.
- **No background workers:** Use cron jobs or Render Cron Jobs (free) instead of Celery workers.
- **750 hours/month:** Enough for one service running 24/7 (730 hrs/month).

**Workaround for cold starts:** Set up a free cron service (like [cron-job.org](https://cron-job.org)) to ping your backend every 14 minutes.

### Neon Free Tier
- **500 MB storage:** Enough for ~50,000 properties with full analysis data.
- **0.25 vCPU:** Sufficient for ~100 concurrent users.
- **Compute auto-suspends** after 5 min idle (300ms cold start).

### Upstash Free Tier
- **10,000 commands/day:** Enough for ~100 active users.
- **256 MB storage:** Plenty for caching and rate limiting.
- **Maxes out at ~7 requests/second** sustained.

### SendGrid Free Tier
- **100 emails/day:** Enough for ~100 deal alert users.
- Use Gmail SMTP as fallback for overflow.

### No Celery Workers
- On free tier, run tasks synchronously or use lightweight alternatives:
  - **Render Cron Jobs** (free) for scheduled scraping
  - **Background tasks** in FastAPI for async processing
  - Upgrade to Render Starter ($7/mo) for always-on workers

---

## Scaling Up When Revenue Justifies It

### Phase 1: First Revenue ($50-100/mo budget)
```
Render Starter ($7/mo) -- eliminates cold starts, adds background workers
Neon Launch ($19/mo) -- 10GB storage, better performance
Upstash Pro ($10/mo) -- 200K commands/day
Custom domain ($1/mo) -- professional appearance
```

### Phase 2: Growing Users ($100-300/mo budget)
```
Render Standard ($25/mo) -- 2 GB RAM, always-on
Neon Scale ($69/mo) -- autoscaling, read replicas
SendGrid Essentials ($20/mo) -- 50K emails/month
Sentry Team ($26/mo) -- better error tracking
```

### Phase 3: Production Scale ($300+/mo budget)
```
AWS ECS or Railway -- auto-scaling containers
RDS PostgreSQL -- managed, high-availability
ElastiCache Redis -- managed, low-latency
Claude API -- premium AI summaries
Datadog -- full observability
```

### Migration Path
Every service upgrade is a simple environment variable change:
1. **Database:** Change `DATABASE_URL` to new provider
2. **Redis:** Change `REDIS_URL` to new provider
3. **AI:** Set `OLLAMA_URL` or swap to Claude API (future feature flag)
4. **Email:** Add `SENDGRID_API_KEY` or change SMTP settings

No code changes needed -- the app is designed to scale through configuration.

---

## Local Development

For local development, everything runs free in Docker:

```bash
# Start all services (PostgreSQL, Redis, backend, frontend)
cd infra
cp .env.example .env
docker compose up -d

# Optional: Add Ollama for local AI
docker compose --profile with-ollama up -d
docker exec realdeal-ollama ollama pull llama3

# Access:
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# API docs: http://localhost:8000/docs
# Ollama:   http://localhost:11434
```

---

## Architecture: What's Free and Why It Works

### Scraping (No BrightData Needed)
The scraper uses direct HTTP requests with:
- 20+ real browser User-Agent strings (rotated per request)
- Browser-mimicking headers (Sec-Fetch-*, Accept-Language, etc.)
- Per-domain rate limiting (max 1 request per 3 seconds)
- Random delays (2-5 seconds between requests)
- Exponential backoff with jitter on failures
- Optional free proxy list support

This is sufficient for moderate-volume scraping (~500-1000 pages/day).

### AI Analysis (No Paid LLM Needed)
All investment analysis is pure math:
- ARV calculation from comparable sales
- Rehab cost estimation from cost tables
- Cash flow, cap rate, DSCR, cash-on-cash -- all formulas
- Investment score -- weighted formula (0-100)
- BRRRR score -- composite formula (0-100)

Summaries are template-generated using actual calculated metrics, producing
4-5 specific pros/cons based on real numbers. The templates are surprisingly
detailed and useful without any LLM.

### Maps (No Mapbox Needed)
Uses Leaflet + OpenStreetMap:
- Free, open-source, no API key required
- No usage limits
- Dark theme via CartoDB tiles (also free)
- Same functionality: markers, popups, layers, legends
