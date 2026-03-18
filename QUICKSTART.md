# 🚀 Quick Start Guide

Get Digital Pulse running in **5 minutes**!

---

## ⚡ Prerequisites

```bash
# Check you have these installed:
node --version  # Need v18+
python --version  # Need 3.10+
```

---

## 📦 Installation

### 1. Clone & Setup Backend
```bash
git clone https://github.com/YOUR_USERNAME/digital-pulse.git
cd digital-pulse/project

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your Supabase credentials
```

### 2. Setup Frontend
```bash
# Open new terminal
cd digital-pulse/project/frontend

npm install
# or
yarn install

# Setup environment
cp .env.local.example .env.local
# Default settings work for local development
```

---

## 🗄️ Database Setup (Supabase)

1. Go to [supabase.com](https://supabase.com) and create a project
2. Copy your project URL and anon key
3. Paste into `.env` file:
   ```
   SUPABASE_URL=https://xxx.supabase.co
   SUPABASE_KEY=your-key-here
   ```
4. Run this SQL in Supabase SQL Editor:

```sql
-- Create posts table
CREATE TABLE posts (
  post_id TEXT PRIMARY KEY,
  title TEXT,
  content TEXT,
  timestamp TIMESTAMPTZ,
  likes INTEGER DEFAULT 0,
  shares INTEGER DEFAULT 0,
  comments INTEGER DEFAULT 0,
  source TEXT,
  region TEXT,
  virality_score NUMERIC,
  engagement_total INTEGER,
  engagement_velocity NUMERIC,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create clusters table
CREATE TABLE clusters (
  cluster_id TEXT PRIMARY KEY,
  label TEXT,
  representative_docs TEXT[],
  keywords TEXT[],
  influence_score NUMERIC,
  size INTEGER,
  centroid JSONB,
  detected_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add indexes for performance
CREATE INDEX idx_posts_timestamp ON posts(timestamp DESC);
CREATE INDEX idx_posts_virality ON posts(virality_score DESC);
CREATE INDEX idx_posts_source ON posts(source);
```

---

## ▶️ Run the App

### Terminal 1 - Backend
```bash
cd project/backend
uvicorn main:app --reload --port 8000
```

**Backend running at:** http://localhost:8000

### Terminal 2 - Frontend
```bash
cd frontend
npm run dev
# or
yarn dev
```

**Frontend running at:** http://localhost:3000

---

## ✅ Verify It Works

1. Open browser: http://localhost:3000
2. Dashboard loads (may be empty initially)
3. Click "Upload CSV" and try sample data
4. Click a narrative → Virality Breakdown updates

---

## 📊 Add Sample Data

### Method 1: CSV Upload (Easiest)

Create `sample.csv`:
```csv
title,content,timestamp,likes,shares,comments,region
"AI Breakthrough Announced","Major AI advancement",2026-03-17T12:00:00Z,150,80,45,"US"
"Climate Action Summit","Global leaders meet",2026-03-17T11:00:00Z,220,120,67,"EU"
"Tech Startup IPO","New unicorn emerges",2026-03-17T10:00:00Z,90,50,23,"US"
```

Upload via dashboard "Upload CSV" button.

### Method 2: Enable Scrapers (Optional)

Edit `.env`:
```
REDDIT_CLIENT_ID=your-id
REDDIT_CLIENT_SECRET=your-secret
NEWSAPI_KEY=your-key
```

Scrapers will run automatically and populate data.

---

## 🐛 Troubleshooting

### "Module not found" errors
```bash
# Backend
pip install -r requirements.txt --force-reinstall

# Frontend
rm -rf node_modules package-lock.json
npm install
```

### Backend won't start
- Check Python version: `python --version` (need 3.10+)
- Check if port 8000 is free: `lsof -i :8000`
- Check Supabase credentials in `.env`

### Frontend shows "API Error"
- Verify backend is running at http://localhost:8000
- Check `.env.local`: `NEXT_PUBLIC_API_URL=http://localhost:8000`
- Check CORS settings in backend

### Database connection fails
- Verify Supabase credentials
- Check tables exist
- Test connection: http://localhost:8000/docs (should load Swagger UI)

### Empty dashboard
- Upload sample CSV data
- Or wait for scrapers to collect data (5-10 minutes)
- Check console logs for errors

---

## 📖 Next Steps

- **Full Documentation**: [README.md](README.md)
- **API Reference**: http://localhost:8000/docs (Swagger UI)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

---

## 🎯 Key Features to Try

1. **Upload CSV** → See instant data visualization
2. **Click Narrative** → View virality breakdown
3. **View Clusters** → Interactive force graph
4. **Check Forecasts** → 24-hour predictions
5. **Export PDF** → Generate report

---

## ⚙️ Configuration

### Adjust Data Limits (for faster demo)
`frontend/pages/index.js`:
```javascript
fetchNarratives({ limit: 20 }),  // ← Change this
fetchEmerging({ limit: 10 }),
fetchForecasts({ limit: 8 }),
```

### Change Theme Colors
`frontend/styles/globals.css`:
```css
:root {
  --primary: #7b61ff;  /* Purple */
  --accent: #00d4ff;   /* Cyan */
}
```

---

## 🚢 Deploy to Production

### Frontend (Vercel)
```bash
cd frontend
vercel --prod
```

### Backend (Render)
1. Push to GitHub
2. Connect to Render
3. Add environment variables
4. Deploy

**See full deployment guide in README.md**

---

## 💬 Get Help

- **GitHub Issues**: [Report bugs](https://github.com/YOUR_USERNAME/digital-pulse/issues)
- **Discussions**: [Ask questions](https://github.com/YOUR_USERNAME/digital-pulse/discussions)
- **Email**: dev@digitalpulse.io

---

## ✨ You're Ready!

Your Digital Pulse dashboard is now running. Start exploring virality intelligence! 🎉

**Tip**: Open browser console (F12) to see detailed debug logs of all interactions.

---

<div align="center">

**Happy Hacking! 🚀**

[Full README](README.md) • [API Docs](http://localhost:8000/docs) • [Contribute](CONTRIBUTING.md)

</div>
