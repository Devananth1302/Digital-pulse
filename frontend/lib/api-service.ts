/**
 * REST API Service for Digital Pulse Analytics
 * Fallback data fetching when WebSocket is unavailable
 */

import { TrendingSignal } from './websocket-service';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

/**
 * Fetch trending signals from REST endpoint
 */
export async function fetchTrendingSignals(limit: number = 50): Promise<TrendingSignal[]> {
  try {
    const response = await fetch(`${API_URL}/api/trending?limit=${limit}`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }

    const data = (await response.json()) as ApiResponse<TrendingSignal[]>;
    return data.data || [];
  } catch (error) {
    console.error('Failed to fetch trending signals:', error);
    return [];
  }
}

/**
 * Fetch trending by industry
 */
export async function fetchTrendingByIndustry(industry: string): Promise<TrendingSignal[]> {
  try {
    const response = await fetch(`${API_URL}/api/trending/industry/${encodeURIComponent(industry)}`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }

    const data = (await response.json()) as ApiResponse<TrendingSignal[]>;
    return data.data || [];
  } catch (error) {
    console.error(`Failed to fetch trends for industry ${industry}:`, error);
    return [];
  }
}

/**
 * Fetch sentiment spikes
 */
export async function fetchSentimentSpikes(limit: number = 10): Promise<TrendingSignal[]> {
  try {
    const response = await fetch(`${API_URL}/api/sentiment-spikes?limit=${limit}`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }

    const data = (await response.json()) as ApiResponse<TrendingSignal[]>;
    return data.data || [];
  } catch (error) {
    console.error('Failed to fetch sentiment spikes:', error);
    return [];
  }
}

/**
 * Get health status of API
 */
export async function checkApiHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_URL}/health`, {
      method: 'HEAD',
    });
    return response.ok;
  } catch (error) {
    console.error('Health check failed:', error);
    return false;
  }
}
