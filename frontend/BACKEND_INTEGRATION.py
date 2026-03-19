"""
Digital Pulse Analytics - FastAPI WebSocket Integration
Add this to backend/main.py to stream Kafka trending_signals to frontend dashboards

USAGE:
1. Copy this entire file or the relevant functions to backend/main.py
2. Import at the top: from fastapi import WebSocket, WebSocketDisconnect
3. Make sure manager = ConnectionManager() is instantiated
4. Add the startup event to run stream_trending_to_websocket
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
import json
import asyncio
import logging
from datetime import datetime
from confluent_kafka import Consumer, KafkaError

# Configure logging
logger = logging.getLogger(__name__)

# ============================================================================
# WEBSOCKET CONNECTION MANAGER
# ============================================================================

class ConnectionManager:
    """Manages active WebSocket connections for broadcasting trending data"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.logger = logging.getLogger(__name__)

    async def connect(self, websocket: WebSocket):
        """Accept and register new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.logger.info(f"✓ Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Unregister closed WebSocket connection"""
        self.active_connections.remove(websocket)
        self.logger.info(f"✗ Client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """Send message to all connected clients"""
        if not self.active_connections:
            return

        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                self.logger.error(f"Failed to send to client: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)


# ============================================================================
# INITIALIZE CONNECTION MANAGER (ADD TO MAIN APP)
# ============================================================================

manager = ConnectionManager()

# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================


async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time analytics streaming
    Location: ws://localhost:8000/ws/analytics (or wss:// for production)
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive by listening for messages
            # In production, you might send periodic pings
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Echo any received messages (optional - mainly for keep-alive)
                logger.debug(f"Received: {data}")
            except asyncio.TimeoutError:
                # No message received within 30 seconds - that's okay
                # Connection is still alive
                continue

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket connection closed normally")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            manager.disconnect(websocket)
        except:
            pass


# ============================================================================
# KAFKA CONSUMER FOR TRENDING SIGNALS
# ============================================================================

async def stream_trending_signals_to_websocket():
    """
    Background task that:
    1. Consumes trending_signals from Kafka
    2. Broadcasts to all connected WebSocket clients
    3. Handles reconnection automatically
    """

    consumer = Consumer(
        {
            "bootstrap.servers": "localhost:9092",
            "group.id": "web-dashboard-subscribers",
            "auto.offset.reset": "latest",
            "session.timeout.ms": 10000,
            "enable.auto.commit": True,
            "api.version.request.timeout.ms": 10000,
        }
    )

    consumer.subscribe(["trending_signals"])
    logger.info("✓ Subscribed to trending_signals topic")

    try:
        message_count = 0
        while True:
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                # No message this interval - that's fine
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    logger.debug("Reached end of partition")
                else:
                    logger.error(f"Kafka error: {msg.error()}")
                continue

            try:
                # Decode and parse message
                signal_data = json.loads(msg.value().decode("utf-8"))

                # Broadcast to all connected clients
                await manager.broadcast(signal_data)

                message_count += 1
                if message_count % 50 == 0:
                    logger.info(
                        f"📊 Broadcast {message_count} trending signals to "
                        f"{manager.get_connection_count()} connected clients"
                    )

            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode message: {e}")
            except Exception as e:
                logger.error(f"Failed to broadcast message: {e}")

    except KeyboardInterrupt:
        logger.info("Streaming interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error in streaming loop: {e}")
    finally:
        consumer.close()
        logger.info("❌ Kafka consumer closed")


# ============================================================================
# REST API ENDPOINTS (Optional Fallback)
# ============================================================================

# Cache for trending signals (in-memory, max 500 records)
_trending_cache: List[Dict[str, Any]] = []
_max_cache_size = 500


def _update_cache(signal: Dict[str, Any]):
    """Update in-memory cache with new signal"""
    global _trending_cache
    _trending_cache.insert(0, {**signal, "_received_at": datetime.now().isoformat()})
    _trending_cache = _trending_cache[:_max_cache_size]


async def cache_signals_from_kafka():
    """Background task to keep cache updated (alternative to broadcasting)"""
    consumer = Consumer(
        {
            "bootstrap.servers": "localhost:9092",
            "group.id": "cache-updater",
            "auto.offset.reset": "latest",
        }
    )

    consumer.subscribe(["trending_signals"])

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg and not msg.error():
                signal = json.loads(msg.value().decode("utf-8"))
                _update_cache(signal)
    except Exception as e:
        logger.error(f"Cache update error: {e}")
    finally:
        consumer.close()


# Add these endpoints to your app:
# @app.get("/api/trending")
# async def get_trending_signals(limit: int = 50):
#     """Fetch recent trending signals from cache"""
#     return {"success": True, "data": _trending_cache[:limit]}
#
#
# @app.get("/api/trending/industry/{industry}")
# async def get_trending_by_industry(industry: str, limit: int = 20):
#     """Fetch trending signals for specific industry"""
#     filtered = [s for s in _trending_cache if s.get("industry") == industry]
#     return {"success": True, "data": filtered[:limit]}
#
#
# @app.get("/api/sentiment-spikes")
# async def get_sentiment_spikes(limit: int = 10):
#     """Fetch recent sentiment spikes"""
#     spikes = [s for s in _trending_cache if s.get("momentum") == "accelerating"]
#     return {"success": True, "data": spikes[:limit]}
#
#
# @app.head("/health")
# async def health_check():
#     """Health check endpoint"""
#     return {"status": "ok"}


# ============================================================================
# INTEGRATION INSTRUCTIONS
# ============================================================================

"""
STEP 1: Add to imports in backend/main.py
    from fastapi import WebSocket, WebSocketDisconnect
    import asyncio
    import json
    from confluent_kafka import Consumer, KafkaError

STEP 2: Add WebSocket route
    @app.websocket("/ws/analytics")
    async def ws_endpoint(websocket: WebSocket):
        await websocket_endpoint(websocket)

STEP 3: Add startup event
    @app.on_event("startup")
    async def startup_event():
        asyncio.create_task(stream_trending_signals_to_websocket())
        # Optional: asyncio.create_task(cache_signals_from_kafka())

STEP 4: (Optional) Enable CORS for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

STEP 5: Test
    - Start backend: python -m uvicorn backend.main:app --reload
    - Start frontend: npm run dev
    - Dashboard should connect and show real-time data
"""
