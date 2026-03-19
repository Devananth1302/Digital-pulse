# Quick Demo: Testing Dashboard Without Full Setup

If you want to see the dashboard working **right now** without waiting to implement the full WebSocket backend, here's a quick mock-up test:

## Option 1: Frontend-only Test (2 minutes)

### Step 1: Update WebSocket Service to Use Mock Data

Edit `frontend/lib/websocket-service.ts` - comment out real WebSocket, add mock:

```typescript
// Around line 140, in the connect() method:

public connect(): Promise<void> {
  return new Promise((resolve) => {
    this.updateConnectionStatus('connected');
    
    // MOCK DATA for testing
    this.mockDataStream();
    resolve();
  });
}

private mockDataStream(): void {
  // Simulate receiving data
  setInterval(() => {
    const mockSignal = {
      signal_type: 'trending' as const,
      industry: ['Technology', 'Finance', 'Healthcare', 'Media'][
        Math.floor(Math.random() * 4)
      ],
      subtopic: ['artificial_intelligence', 'blockchain', 'cybersecurity', 'quantum_computing'][
        Math.floor(Math.random() * 4)
      ],
      trending_score: Math.random() * 0.5 + 0.5,
      momentum: ['accelerating', 'growing', 'stable'][Math.floor(Math.random() * 3)],
      posts: [
        {
          title: 'Breaking: Major advancement announced',
          content: 'Industry leaders announce groundbreaking development...',
          engagement_total: Math.floor(Math.random() * 50000),
          likes: Math.floor(Math.random() * 30000),
          shares: Math.floor(Math.random() * 5000),
          comments: Math.floor(Math.random() * 15000),
          velocity: Math.random() * 500 + 50,
          timestamp: new Date().toISOString(),
        },
      ],
    };
    
    this.handleNewData(mockSignal);
  }, 2000); // New signal every 2 seconds
}
```

### Step 2: Start Frontend

```bash
cd frontend
npm run dev
# Open http://localhost:3000/analytics
```

**Result:** Dashboard shows mock data with real-time updates, drill-down functionality, and animations working perfectly!

---

## Option 2: Quick Backend Mock (5 minutes)

### Step 1: Create Mock WebSocket Endpoint

Create `backend/routes/ws_mock.py`:

```python
from fastapi import WebSocket, WebSocketDisconnect
import json
import random
import asyncio

class MockConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast_mock_data(self):
        industries = ['Technology', 'Finance', 'Healthcare', 'Media']
        subtopics = ['artificial_intelligence', 'blockchain', 'cybersecurity', 'quantum_computing']
        
        while True:
            await asyncio.sleep(2)  # New signal every 2 seconds
            
            signal = {
                'signal_type': 'trending',
                'industry': random.choice(industries),
                'subtopic': random.choice(subtopics),
                'trending_score': random.uniform(0.5, 1.0),
                'rank': random.randint(1, 5),
                'window_hours': 1,
                'momentum': random.choice(['accelerating', 'growing', 'stable']),
                'posts': [
                    {
                        'title': f'Breaking: {random.choice(["Announcement", "Release", "Discovery", "Update"])} in {random.choice(subtopics)}',
                        'content': 'Industry leaders announce groundbreaking development that will reshape the market...',
                        'engagement_total': random.randint(5000, 50000),
                        'likes': random.randint(3000, 30000),
                        'shares': random.randint(500, 5000),
                        'comments': random.randint(1000, 15000),
                        'velocity': random.uniform(50, 500),
                        'timestamp': datetime.now().isoformat(),
                    }
                ],
                'clustered_at': datetime.now().isoformat(),
            }
            
            for connection in self.active_connections:
                try:
                    await connection.send_json(signal)
                except:
                    pass

mock_manager = MockConnectionManager()

@router.websocket("/ws/analytics")
async def websocket_endpoint(websocket: WebSocket):
    await mock_manager.connect(websocket)
    
    # Start broadcasting mock data
    asyncio.create_task(mock_manager.broadcast_mock_data())
    
    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        mock_manager.disconnect(websocket)
```

### Step 2: Add Route to main.py

```python
# In backend/main.py
from backend.routes.ws_mock import router as ws_router
app.include_router(ws_router)
```

### Step 3: Start Backend & Frontend

```bash
# Terminal 1
cd backend
python -m uvicorn main:app --reload

# Terminal 2
cd frontend
npm run dev
```

**Result:** Dashboard connects to mock WebSocket and shows simulated real-time data!

---

## Option 3: Hybrid - Mock Backend + Real Processors (10 minutes)

This simulates having the real backend but without Kafka:

### Step 1: Create Simple Producer to Mock Topic

```python
# backend/test_producer.py
from confluent_kafka import Producer
import json
import time
import random

producer = Producer({'bootstrap.servers': 'localhost:9092'})

industries = ['Technology', 'Finance', 'Healthcare']
subtopics = ['artificial_intelligence', 'blockchain', 'cybersecurity']

def delivery_report(err, msg):
    if err: print(f'Message failed: {err}')
    else: print(f'Message sent: {msg.topic()}')

for i in range(100):
    signal = {
        'signal_type': 'trending',
        'industry': random.choice(industries),
        'subtopic': random.choice(subtopics),
        'trending_score': random.uniform(0.5, 1.0),
        'posts': [{'title': f'Article {i}', 'content': 'Content...', 'engagement_total': random.randint(1000, 10000)}],
    }
    
    producer.produce(
        'trending_signals',
        json.dumps(signal).encode('utf-8'),
        callback=delivery_report
    )
    
    time.sleep(0.5)

producer.flush()
print('✓ Produced 100 test signals')
```

### Step 2: Run Everything

```bash
# Terminal 1: Kafka
docker-compose -f docker-compose.kafka.yml up -d

# Terminal 2: Producer (fill topic with test data)
python backend/test_producer.py

# Terminal 3: Backend with real WebSocket
python -m uvicorn backend.main:app --reload

# Terminal 4: Frontend
npm run dev
```

**Result:** Dashboard receives REAL Kafka data (not mock), but you didn't need to run processorsyet!

---

## Demo Checklist

- [ ] See industries loading in grid
- [ ] See real-time score updates
- [ ] Click industry → drill to subtopics
- [ ] Click subtopic → drill to posts
- [ ] See engagement metrics
- [ ] Connection status shows 🟢 LIVE
- [ ] No console errors
- [ ] Responsive on mobile

---

## Next: Full Integration

Once you're comfortable with the dashboard:

1. Implement real WebSocket endpoint in backend (see BACKEND_INTEGRATION.py)
2. Run full processor pipeline (run-pipeline)
3. Dashboard will start receiving real trending_signals
4. Remove mock data stream
5. Go live!

---

**Ready to see it working? Pick an option above and run it! 🚀**
