# 🔐 ENVIRONMENT VARIABLES TEMPLATE
## Digital Pulse - Configuration Reference

**Copy and fill with your credentials**

---

## Backend Configuration (.env)

```bash
# ═══════════════════════════════════════════════════════════════════════
# SUPABASE - Database Connection
# Get from: https://supabase.com → Project Settings → API
# ═══════════════════════════════════════════════════════════════════════
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-supabase-anon-key-here

# ═══════════════════════════════════════════════════════════════════════
# NEWS API - News Source Aggregation
# Get from: https://newsapi.org → Dashboard → API Keys
# Free tier: 500 requests/day (sufficient for development)
# ═══════════════════════════════════════════════════════════════════════
NEWS_API_KEY=your-newsapi-key-here

# ═══════════════════════════════════════════════════════════════════════
# REDDIT API (Optional)
# Get from: https://www.reddit.com/prefs/apps → Create app
# Not required for basic functionality - Reddit scraping is optional
# ═══════════════════════════════════════════════════════════════════════
# REDDIT_CLIENT_ID=your-reddit-client-id
# REDDIT_CLIENT_SECRET=your-reddit-client-secret

# ═══════════════════════════════════════════════════════════════════════
# APPLICATION CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════
APP_ENV=development                    # development | staging | production
SCRAPE_INTERVAL_MINUTES=15             # How often to ingest data (15-30 recommended)
FRONTEND_URL=http://localhost:3000     # React app URL (used for CORS)
BACKEND_URL=http://localhost:8000      # FastAPI server URL

# ═══════════════════════════════════════════════════════════════════════
# VIRALITY SCORING WEIGHTS (Advanced Tuning)
# These coefficients determine virality calculation
# Should sum to approximately 1.0
# ═══════════════════════════════════════════════════════════════════════
VIRALITY_WEIGHT_SHARES=0.4             # Share contribution (40%)
VIRALITY_WEIGHT_COMMENTS=0.3           # Comment contribution (30%)
VIRALITY_WEIGHT_LIKES=0.2              # Like contribution (20%)
VIRALITY_WEIGHT_VELOCITY=0.1           # Velocity contribution (10%)

# ═══════════════════════════════════════════════════════════════════════
# EMERGING SIGNAL DETECTION THRESHOLDS
# ═══════════════════════════════════════════════════════════════════════
EMERGING_GROWTH_RATE_THRESHOLD=1.5     # Minimum growth factor (1.5 = 50% growth)
EMERGING_TIME_WINDOW_HOURS=6           # Rolling window size (6 hours)

# ═══════════════════════════════════════════════════════════════════════
# KAFKA (For Advanced Users - Uncomment if using local Kafka)
# Requires: docker-compose -f docker-compose.kafka.yml up
# ═══════════════════════════════════════════════════════════════════════
# KAFKA_BOOTSTRAP_SERVERS=localhost:9092
# KAFKA_TOPIC_RAW_POSTS=raw_posts
# KAFKA_TOPIC_PROCESSED=processed_results
```

---

## Frontend Configuration (.env.local)

```bash
# ═══════════════════════════════════════════════════════════════════════
# API ENDPOINT
# Point frontend to backend server
# ═══════════════════════════════════════════════════════════════════════
NEXT_PUBLIC_API_URL=http://localhost:8000

# ═══════════════════════════════════════════════════════════════════════
# FEATURE FLAGS (Optional - Uncomment to customize)
# ═══════════════════════════════════════════════════════════════════════
# NEXT_PUBLIC_ENABLE_FORECAST=true
# NEXT_PUBLIC_ENABLE_EMERGING_SIGNALS=true
# NEXT_PUBLIC_DEMO_MODE=false

# ═══════════════════════════════════════════════════════════════════════
# ANALYTICS (Optional - If using Google Analytics)
# ═══════════════════════════════════════════════════════════════════════
# NEXT_PUBLIC_GA_ID=your-google-analytics-id
```

---

## 📋 Setup Checklist

- [ ] Backend `.env` created in project root
- [ ] Frontend `.env.local` created in `frontend/` directory
- [ ] Supabase URL and Key populated
- [ ] NewsAPI key obtained and added
- [ ] `npm run dev` runs without env errors
- [ ] `uvicorn main:app --reload` runs without env errors
- [ ] Backend API accessible at http://localhost:8000
- [ ] Frontend accessible at http://localhost:3000
- [ ] Dashboard displays data (not blank)

---

## 🔍 Validation Commands

```bash
# Test backend environment
python -c "from config.settings import settings; print(f'✓ Backend: {settings.BACKEND_URL}')"

# Test Supabase connection
python -c "from backend.core.database import client; print('✓ Supabase OK')"

# Test frontend environment
cd frontend && npm run build 2>&1 | head -20

# Test API connectivity
curl http://localhost:8000/ | jq .
```

---

## 🚀 Production Deployment Template

### Backend (Render, Railway, Heroku)

```bash
# Copy these environment variables to your hosting platform's dashboard

APP_ENV=production
SUPABASE_URL=https://prod-project.supabase.co
SUPABASE_KEY=prod-key-xxxxxxxxxxxx
NEWS_API_KEY=prod-key-xxxxxxxxxxxx
FRONTEND_URL=https://yourdomain.com
BACKEND_URL=https://api.yourdomain.com
SCRAPE_INTERVAL_MINUTES=30
```

### Frontend (Vercel)

```bash
# Vercel Environment Variables

NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

---

## ⚠️ Security Best Practices

✅ **DO:**
- Store `.env` files in `.env` (never commit to git)
- Use `.env.example` as template for contributors
- Rotate keys regularly (especially in production)
- Add `.env` to `.gitignore`
- Use long, randomly generated API keys
- Keep backend keys secret (never expose in frontend)

❌ **DON'T:**
- Commit `.env` to version control
- Share `.env` files via email or Slack
- Use same keys for local/staging/production
- Expose `SUPABASE_KEY` in frontend (it's already public)
- Check secrets into documentation

---

## 🆘 Troubleshooting

| Error | Solution |
|-------|----------|
| `KeyError: 'SUPABASE_URL'` | `.env` not found or incomplete. Check file exists in project root. |
| `newsapi.NewsAPIError: 401` | Invalid NEWS_API_KEY. Regenerate at https://newsapi.org/dashboard |
| `Database connection refused` | Supabase URL unreachable. Verify URL is correct and project is active. |
| `CORS error in browser` | Check `FRONTEND_URL` matches actual frontend location (e.g., :3000, not :3001). |
| `Module not found: dotenv` | Python dependencies not installed: `pip install python-dotenv` |

---

**Last Updated**: March 20, 2026  
**For Issues**: Check SRS.md Section 3.10 for detailed troubleshooting
