/**
 * Custom React hooks for analytics data
 */
import { useState, useEffect } from 'react';
import { getWebSocketService, TrendingSignal, AnalyticsState } from '@/lib/websocket-service';

/**
 * Hook to manage WebSocket connection and state
 */
export function useAnalyticsStream() {
  const [state, setState] = useState<AnalyticsState | null>(null);
  const [status, setStatus] = useState<'connected' | 'connecting' | 'disconnected' | 'error'>('disconnected');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const wsService = getWebSocketService();

    // Subscribe to state updates
    const unsubscribeState = wsService.onStateChange((newState) => {
      setState(newState);
      setIsLoading(false);
    });

    // Subscribe to status updates
    const unsubscribeStatus = wsService.onStatusChange(setStatus);

    // Connect
    wsService.connect().catch((err) => {
      console.error('Failed to connect:', err);
      setIsLoading(false);
    });

    // Cleanup
    return () => {
      unsubscribeState();
      unsubscribeStatus();
    };
  }, []);

  return { state, status, isLoading };
}

/**
 * Hook to subscribe to new trending signals
 */
export function useTrendingSignals(callback: (data: TrendingSignal | TrendingSignal[]) => void) {
  useEffect(() => {
    const wsService = getWebSocketService();
    return wsService.onData(callback);
  }, [callback]);
}

/**
 * Hook to get trends by industry
 */
export function useTrendsByIndustry(industry: string): TrendingSignal[] {
  const { state } = useAnalyticsStream();
  return state?.topIndustries.get(industry) || [];
}
