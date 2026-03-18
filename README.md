# 🚀 Digital Pulse - Real-Time Virality Intelligence Platform

<div align="center">

![Digital Pulse](https://img.shields.io/badge/Digital-Pulse-7b61ff?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Live-00ff88?style=for-the-badge)
![Hackathon](https://img.shields.io/badge/Hackathon-Ready-ff3d8e?style=for-the-badge)

**Monitor, Analyze, and Predict Digital Content Virality in Real-Time**

[Features](#-features) • [Demo](#-demo) • [Tech Stack](#-tech-stack) • [Quick Start](#-quick-start) • [API Docs](#-api-documentation)

</div>

---

## 📖 Overview

**Digital Pulse** is an AI-powered real-time intelligence platform that tracks, analyzes, and predicts content virality across multiple digital sources. Built for hackathons, it combines cutting-edge ML models with an intuitive dashboard to deliver actionable insights on trending narratives, emerging signals, and engagement forecasts.

### 💡 The Problem We Solve

In today's fast-paced digital landscape:
- **Content creators** need to know what's trending NOW
- **Marketers** need to predict viral content before it peaks
- **Researchers** need to understand narrative clustering patterns
- **Organizations** need real-time pulse on digital conversations

**Digital Pulse** provides all of this in a single, beautiful dashboard.

---

## ✨ Features

### 🎯 Core Features

- ⚡ **Real-Time Pulse Score** - Live tracking of overall digital engagement intensity
- 📊 **Virality Breakdown** - Deep analysis of what makes content go viral (shares, comments, likes, velocity)
- 🌐 **Multi-Source Aggregation** - Reddit, Google News, NewsAPI, CSV uploads
- 🧠 **AI-Powered Clustering** - BERTopic-based narrative grouping with influence scoring
- 📈 **Engagement Forecasts** - Predict content performance 24 hours ahead
- 🚨 **Emerging Signals** - Early detection of trending topics
- 🗺️ **Regional Heatmaps** - Geographic distribution of engagement
- 📄 **PDF Reports** - Export complete analytics with one click

### 🚀 Advanced Features

- 🔄 **CSV Import** - Upload custom datasets instantly
- 🎨 **Interactive Visualizations** - D3.js force-directed graphs, Recharts
- 📱 **Responsive Design** - Works on desktop, tablet, and mobile
- 🔍 **Smart Fallbacks** - Simulated metrics when API data unavailable
- ⚙️ **Performance Optimized** - useMemo, React.memo, data limiting
- 🎭 **Demo Mode** - Disabled auto-fetch for smooth presentations

---

## 🎬 Demo

### Dashboard Views

**Main Dashboard**
```
┌─────────────────────────────────────────────────────────┐
│  Digital Pulse Score: 73.4  ↑12%                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Trending │  │ Emerging │  │ Regional │              │
│  │Narratives│  │ Signals  │  │ Heatmap  │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│  ┌────────────────────────────────────────┐            │
│  │     Cluster Network Visualization      │            │
│  │        (D3.js Force Graph)             │            │
│  └────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────┘
```

**Virality Breakdown Panel**
- Total Score: 87.3
- Shares: 40% | Comments: 30% | Likes: 20% | Velocity: 10%
- Momentum: 🚀 Accelerating +25%
- Engagement: 142/hour

---

## 🛠️ Tech Stack

### Frontend
- **Framework**: [Next.js 14](https://nextjs.org/) (React 18)
- **Styling**: Custom CSS with Glass Morphism
- **Charts**: [Recharts](https://recharts.org/), [D3.js](https://d3js.org/)
- **Data Processing**: PapaParse, useMemo optimization
- **Export**: jsPDF, html2canvas

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+)
- **Database**: [Supabase](https://supabase.com/) (PostgreSQL)
- **AI/ML**:
  - [BERTopic](https://maartengr.github.io/BERTopic/) - Topic modeling
  - [Sentence-Transformers](https://www.sbert.net/) - Embeddings
  - [HDBSCAN](https://hdbscan.readthedocs.io/) - Clustering
- **Scraping**: httpx, feedparser
- **Scheduling**: APScheduler

### Infrastructure
- **Deployment**: Render/Vercel ready
- **API**: RESTful with async/await
- **Caching**: In-memory 30s TTL
- **CORS**: Configured for production

---

## 🚀 Quick Start

### Prerequisites
```bash
# Check versions
node --version  # v18+ required
python --version  # 3.10+ required
```

### 1. Clone Repository
```bash
git clone https://github.com/YOUR_USERNAME/digital-pulse.git
cd digital-pulse
```

### 2. Backend Setup
```bash
# Navigate to project root
cd project

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Supabase credentials

# Run backend
cd backend
uvicorn main:app --reload --port 8000
```

**Backend will be available at:** `http://localhost:8000`

### 3. Frontend Setup
```bash
# Open new terminal
cd frontend

# Install dependencies
npm install
# or
yarn install

# Configure environment
cp .env.local.example .env.local
# Edit .env.local: NEXT_PUBLIC_API_URL=http://localhost:8000

# Run frontend
npm run dev
# or
yarn dev
```

**Frontend will be available at:** `http://localhost:3000`

### 4. Database Setup

**Create Supabase Tables:**

```sql
-- posts table
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

-- clusters table
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

-- Add indexes
CREATE INDEX idx_posts_timestamp ON posts(timestamp DESC);
CREATE INDEX idx_posts_virality ON posts(virality_score DESC);
CREATE INDEX idx_posts_source ON posts(source);
```

---

## 📚 Project Structure

```
digital-pulse/
├── frontend/                # Next.js React frontend
│   ├── components/          # UI components
│   │   ├── ClusterGraph.js  # D3.js visualization
│   │   ├── NarrativeTable.js # Main data table
│   │   ├── ViralityBreakdown.js
│   │   ├── CSVUpload.js
│   │   └── ...
│   ├── pages/
│   │   └── index.js         # Main dashboard
│   ├── lib/
│   │   ├── api.js           # API client
│   │   └── safeUtils.js     # Safety utilities
│   └── styles/              # Global styles
│
├── backend/                 # FastAPI backend
│   ├── api/                 # API routes
│   │   ├── narratives.py
│   │   ├── emerging.py
│   │   ├── forecast.py
│   │   └── pulse.py
│   ├── pipelines/           # Data processing
│   │   ├── virality.py
│   │   ├── clustering.py
│   │   └── forecasting.py
│   ├── scrapers/            # Data collection
│   │   ├── reddit.py
│   │   ├── google_news.py
│   │   └── newsapi.py
│   ├── services/            # Business logic
│   └── main.py              # FastAPI app
│
├── database/                # Schema & migrations
├── config/                  # Configuration files
├── tests/                   # Unit & integration tests
└── requirements.txt         # Python dependencies
```

---

## 📡 API Documentation

### Base URL
```
http://localhost:8000
```

### Endpoints

#### 1. Get Pulse Score
```http
GET /pulse-score
```

**Response:**
```json
{
  "pulse_score": 73.4,
  "trend": 12.5,
  "total_posts": 1234,
  "high_virality_count": 45,
  "avg_engagement": 89.2
}
```

#### 2. Get Narratives (with Clustering)
```http
GET /narratives?limit=20
```

**Response:**
```json
{
  "posts": [...],
  "clusters": [
    {
      "cluster_id": "CL_1",
      "label": "AI Technology Discussion",
      "size": 15,
      "influence_score": 0.87,
      "keywords": ["AI", "machine learning", "GPT"]
    }
  ]
}
```

#### 3. Get Narrative Detail
```http
GET /narratives/{post_id}
```

**Response:**
```json
{
  "post": {...},
  "virality_breakdown": {
    "total_score": 87.3,
    "shares_component": 35.2,
    "comments_component": 26.4,
    "likes_component": 17.6,
    "velocity_component": 8.1,
    "momentum": 1.25,
    "momentum_label": "accelerating",
    "primary_driver": "shares"
  }
}
```

#### 4. Get Emerging Signals
```http
GET /emerging?limit=10
```

#### 5. Get Forecasts
```http
GET /forecast?limit=8
```

#### 6. Upload CSV
```http
POST /upload-csv
Content-Type: multipart/form-data

body: { file: File }
```

**CSV Format:**
```csv
title,content,timestamp,likes,shares,comments,region
"Breaking News","Content here",2024-03-17T12:00:00Z,100,50,25,"US"
```

---

## ⚡ Performance Optimizations

### Frontend
- ✅ **Data Limiting**: Top 15 clusters, 20 posts, 10 signals
- ✅ **Memoization**: useMemo for expensive calculations
- ✅ **Component Memoization**: React.memo on all components
- ✅ **Dynamic Imports**: Lazy loading D3.js, Recharts
- ✅ **Demo Mode**: Auto-refresh disabled (manual control)
- ✅ **Smart Fallbacks**: Simulated data when API unavailable

### Backend
- ✅ **Async/Await**: Non-blocking I/O operations
- ✅ **Response Caching**: 30-second TTL
- ✅ **Database Indexing**: Optimized queries
- ✅ **Connection Pooling**: Supabase client reuse
- ✅ **Batch Processing**: Cluster updates every 5 minutes

### Database
- ✅ **Indexed Columns**: timestamp, virality_score, source
- ✅ **Query Limits**: LIMIT clauses on all queries
- ✅ **Efficient Joins**: Minimal JOIN operations

---

## 🧪 Testing

### Run Frontend Tests
```bash
cd frontend
npm run test
```

### Run Backend Tests
```bash
cd backend
pytest tests/ -v
```

### Manual Testing Checklist
- [ ] Dashboard loads within 3 seconds
- [ ] Click narrative → Virality Breakdown updates
- [ ] Upload CSV → Data appears instantly
- [ ] Cluster graph renders smoothly
- [ ] Charts display correctly
- [ ] Modal opens on card click
- [ ] PDF export works
- [ ] All console logs show correct flow

---

## 🐛 Debugging

### Frontend Debug Mode
All interactions log to console with emoji prefixes:
- 🔵 User action initiated
- 🔄 API call started
- ✅ Success response
- ⚠️ Warning/fallback triggered
- ❌ Error occurred

**Example console output:**
```
🔵 [NarrativeTable] Row clicked: AI breakthrough announced
🔄 [NarrativeTable] Fetching detail for: POST_123
✅ [NarrativeTable] API Response: {...}
📊 [NarrativeTable] Using API breakdown
🎯 [Dashboard] selectedPost updated
📈 [ViralityBreakdown] Processing breakdown
```

### Backend Logs
```bash
# View uvicorn logs
tail -f logs/app.log

# Debug mode
uvicorn main:app --reload --log-level debug
```

---

## 🎨 Customization

### Change Theme Colors
Edit `frontend/styles/globals.css`:
```css
:root {
  --primary: #7b61ff;    /* Purple */
  --accent: #00d4ff;     /* Cyan */
  --success: #00ff88;    /* Green */
  --danger: #ff3d8e;     /* Pink */
}
```

### Adjust Data Limits
Edit `frontend/pages/index.js`:
```javascript
fetchNarratives({ limit: 20 }),  // Change limit
fetchEmerging({ limit: 10 }),
fetchForecasts({ limit: 8 }),
```

### Modify Clustering Algorithm
Edit `backend/pipelines/clustering.py`:
```python
topic_model = BERTopic(
    min_topic_size=5,  # Adjust cluster size
    nr_topics=15,      # Max clusters
)
```

---

## 🚢 Deployment

### Deploy Frontend (Vercel)
```bash
cd frontend
vercel --prod
```

### Deploy Backend (Render)
```yaml
# render.yaml
services:
  - type: web
    name: digital-pulse-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

### Environment Variables

**Frontend (.env.local):**
```
NEXT_PUBLIC_API_URL=https://your-api.render.com
```

**Backend (.env):**
```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your-key-here
REDDIT_CLIENT_ID=your-id
REDDIT_CLIENT_SECRET=your-secret
NEWSAPI_KEY=your-key
```

---

## 📊 Architecture Diagram

```
┌─────────────┐      HTTP/REST      ┌──────────────┐
│   Next.js   │ ←─────────────────→ │   FastAPI    │
│  Frontend   │                     │   Backend    │
└─────────────┘                     └──────────────┘
       │                                    │
       │                                    │
       ↓                                    ↓
┌─────────────┐                     ┌──────────────┐
│   Browser   │                     │  Supabase    │
│   Cache     │                     │  PostgreSQL  │
└─────────────┘                     └──────────────┘
                                           ↑
                                           │
                                    ┌──────────────┐
                                    │   Scrapers   │
                                    │   (Reddit,   │
                                    │  News APIs)  │
                                    └──────────────┘
```

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Code Standards
- Frontend: ESLint + Prettier
- Backend: Black + Flake8
- Write tests for new features
- Update documentation

---

## 📝 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 👥 Team

Built with ❤️ by the Digital Pulse Team for [Hackathon Name]

- **Frontend Lead**: Your Name
- **Backend Lead**: Your Name
- **ML Engineer**: Your Name
- **UI/UX Designer**: Your Name

---

## 🙏 Acknowledgments

- [BERTopic](https://maartengr.github.io/BERTopic/) for topic modeling
- [Supabase](https://supabase.com/) for database infrastructure
- [Recharts](https://recharts.org/) for beautiful charts
- [D3.js](https://d3js.org/) for network visualizations
- [FastAPI](https://fastapi.tiangolo.com/) for blazing-fast API

---

## 📞 Contact

- **Website**: https://digital-pulse.vercel.app
- **Email**: team@digitalpulse.io
- **Discord**: [Join our server](https://discord.gg/digitalpulse)
- **Twitter**: [@DigitalPulseAI](https://twitter.com/digitalpulseai)

---

## 🎯 Roadmap

### Version 2.0 (Planned)
- [ ] Real-time WebSocket updates
- [ ] Multi-language support
- [ ] Sentiment analysis integration
- [ ] Custom alert triggers
- [ ] Mobile app (React Native)
- [ ] Chrome extension
- [ ] API rate limiting
- [ ] User authentication
- [ ] Team collaboration features
- [ ] Advanced ML models (GPT integration)

---

<div align="center">

**⭐ Star this repo if you find it useful!**

Made with 🚀 for Digital Intelligence

[Report Bug](https://github.com/YOUR_USERNAME/digital-pulse/issues) • [Request Feature](https://github.com/YOUR_USERNAME/digital-pulse/issues) • [Documentation](https://docs.digitalpulse.io)

</div>
