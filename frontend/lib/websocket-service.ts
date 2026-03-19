/**
 * Real-time WebSocket Service for Digital Pulse Analytics
 * Receives streaming data from Kafka trending_signals topic via FastAPI WebSocket
 */

export interface TrendingSignal {
  post_id?: string;                    // NEW: Post identifier
  title?: string;                      // NEW: Post title
  content?: string;                    // NEW: Post content preview
  timestamp?: string | Date;           // NEW: Post timestamp
  source?: string;                     // NEW: Data source
  
  signal_type: 'trending' | 'sentiment_spike' | 'emerging';
  industry: string;
  industry_score?: number;
  subtopic: string;
  subtopic_count?: number;
  rank?: number;
  trending_score: number;
  window_hours?: number;
  window_end?: string;
  clustered_at?: string;
  posts: any[];
  engagement_total?: number;
  velocity?: number;
  momentum?: string;
  sentiment?: number;
  likes?: number;                      // NEW: Engagement metrics
  shares?: number;                     // NEW: Engagement metrics
  comments?: number;                   // NEW: Engagement metrics
}

export interface AnalyticsState {
  trendingSignals: TrendingSignal[];
  topIndustries: Map<string, TrendingSignal[]>;
  sentimentSpikes: TrendingSignal[];
  lastUpdate: Date | null;
  connectionStatus: 'connected' | 'connecting' | 'disconnected' | 'error';
}

type DataUpdateCallback = (data: TrendingSignal | TrendingSignal[]) => void;
type StateUpdateCallback = (state: AnalyticsState) => void;
type ConnectionStatusCallback = (status: AnalyticsState['connectionStatus']) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;
  
  private state: AnalyticsState = {
    trendingSignals: [],
    topIndustries: new Map(),
    sentimentSpikes: [],
    lastUpdate: null,
    connectionStatus: 'disconnected',
  };

  private dataCallbacks: DataUpdateCallback[] = [];
  private stateCallbacks: StateUpdateCallback[] = [];
  private statusCallbacks: ConnectionStatusCallback[] = [];

  constructor() {
    // Get backend URL from environment or default
    const protocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss' : 'ws';
    const host = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
    const port = process.env.NEXT_PUBLIC_API_PORT || '8000';
    this.url = `${protocol}://${host}:${port}/ws/analytics`;
  }

  /**
   * Connect to WebSocket and start receiving real-time data
   */
  public connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        resolve();
        return;
      }

      try {
        this.updateConnectionStatus('connecting');
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          console.log('✓ Connected to real-time analytics stream');
          this.reconnectAttempts = 0;
          this.updateConnectionStatus('connected');
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data) as TrendingSignal;
            this.handleNewData(data);
          } catch (err) {
            console.error('Failed to parse WebSocket message:', err);
          }
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.updateConnectionStatus('error');
          reject(error);
        };

        this.ws.onclose = () => {
          console.log('WebSocket disconnected');
          this.updateConnectionStatus('disconnected');
          this.attemptReconnect();
        };
      } catch (err) {
        console.error('Failed to create WebSocket:', err);
        this.updateConnectionStatus('error');
        reject(err);
      }
    });
  }

  /**
   * Disconnect from WebSocket
   */
  public disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.updateConnectionStatus('disconnected');
  }

  /**
   * Handle incoming trending signal data
   */
  private handleNewData(signal: TrendingSignal): void {
    // Add to trending signals (keep last 50)
    this.state.trendingSignals = [signal, ...this.state.trendingSignals].slice(0, 50);

    // Group by industry for drill-down view
    const industryKey = signal.industry || 'Unknown';
    if (!this.state.topIndustries.has(industryKey)) {
      this.state.topIndustries.set(industryKey, []);
    }
    const industrySignals = this.state.topIndustries.get(industryKey)!;
    industrySignals.unshift(signal);
    if (industrySignals.length > 20) {
      industrySignals.pop();
    }

    // Track sentiment spikes
    if (signal.signal_type === 'sentiment_spike' || signal.momentum === 'accelerating') {
      this.state.sentimentSpikes = [signal, ...this.state.sentimentSpikes].slice(0, 10);
    }

    this.state.lastUpdate = new Date();

    // Notify all listeners
    this.notifyDataListeners(signal);
    this.notifyStateListeners();
  }

  /**
   * Attempt to reconnect with exponential backoff
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      this.updateConnectionStatus('error');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    console.log(`Attempting to reconnect in ${delay}ms... (attempt ${this.reconnectAttempts})`);

    setTimeout(() => {
      this.connect().catch((err) => {
        console.error('Reconnection failed:', err);
      });
    }, delay);
  }

  /**
   * Subscribe to data updates
   */
  public onData(callback: DataUpdateCallback): () => void {
    this.dataCallbacks.push(callback);
    return () => {
      this.dataCallbacks = this.dataCallbacks.filter((cb) => cb !== callback);
    };
  }

  /**
   * Subscribe to state updates
   */
  public onStateChange(callback: StateUpdateCallback): () => void {
    this.stateCallbacks.push(callback);
    // Send current state immediately
    callback(this.getState());
    return () => {
      this.stateCallbacks = this.stateCallbacks.filter((cb) => cb !== callback);
    };
  }

  /**
   * Subscribe to connection status changes
   */
  public onStatusChange(callback: ConnectionStatusCallback): () => void {
    this.statusCallbacks.push(callback);
    callback(this.state.connectionStatus);
    return () => {
      this.statusCallbacks = this.statusCallbacks.filter((cb) => cb !== callback);
    };
  }

  /**
   * Get current state snapshot
   */
  public getState(): AnalyticsState {
    return {
      ...this.state,
      topIndustries: new Map(this.state.topIndustries), // Clone map
    };
  }

  /**
   * Get trends by industry
   */
  public getTrendsByIndustry(industry: string): TrendingSignal[] {
    return this.state.topIndustries.get(industry) || [];
  }

  /**
   * Notify data listeners
   */
  private notifyDataListeners(data: TrendingSignal): void {
    this.dataCallbacks.forEach((callback) => {
      try {
        callback(data);
      } catch (err) {
        console.error('Error in data callback:', err);
      }
    });
  }

  /**
   * Notify state listeners
   */
  private notifyStateListeners(): void {
    const state = this.getState();
    this.stateCallbacks.forEach((callback) => {
      try {
        callback(state);
      } catch (err) {
        console.error('Error in state callback:', err);
      }
    });
  }

  /**
   * Update and notify connection status
   */
  private updateConnectionStatus(status: AnalyticsState['connectionStatus']): void {
    this.state.connectionStatus = status;
    this.statusCallbacks.forEach((callback) => {
      try {
        callback(status);
      } catch (err) {
        console.error('Error in status callback:', err);
      }
    });
  }
}

// Singleton instance
let wsServiceInstance: WebSocketService | null = null;

export function getWebSocketService(): WebSocketService {
  if (!wsServiceInstance) {
    wsServiceInstance = new WebSocketService();
  }
  return wsServiceInstance;
}

export default WebSocketService;
