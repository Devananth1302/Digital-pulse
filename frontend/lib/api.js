const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const DEFAULT_TIMEOUT = 8000; // 8 seconds

// Simple in-memory cache
const cache = new Map();
const CACHE_TTL = 30000; // 30 seconds

async function apiFetch(path, options = {}, useCache = true) {
  const cacheKey = path;

  // Check cache first
  if (useCache && cache.has(cacheKey)) {
    const { data, timestamp } = cache.get(cacheKey);
    if (Date.now() - timestamp < CACHE_TTL) {
      return data;
    }
    cache.delete(cacheKey);
  }

  // Create AbortController for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT);

  try {
    const res = await fetch(`${API_URL}${path}`, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) throw new Error(`API ${res.status}`);
    const data = await res.json();

    // Cache successful GET responses
    if (useCache && (!options.method || options.method === 'GET')) {
      cache.set(cacheKey, { data, timestamp: Date.now() });
    }

    return data;
  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      console.error(`API timeout [${path}]`);
    } else {
      console.error(`API error [${path}]:`, err);
    }
    return null;
  }
}

export function clearCache() {
  cache.clear();
}

export async function fetchPosts(params = {}) {
  const query = new URLSearchParams(params).toString();
  return apiFetch(`/posts?${query}`);
}

export async function fetchNarratives(params = {}) {
  const query = new URLSearchParams(params).toString();
  return apiFetch(`/narratives?${query}`);
}

export async function fetchNarrativeDetail(postId) {
  return apiFetch(`/narratives/${postId}`);
}

export async function fetchEmerging(params = {}) {
  const query = new URLSearchParams(params).toString();
  return apiFetch(`/emerging?${query}`);
}

export async function fetchPulseScore() {
  return apiFetch('/pulse-score');
}

export async function fetchForecasts(params = {}) {
  const query = new URLSearchParams(params).toString();
  return apiFetch(`/forecast?${query}`);
}

export async function uploadCSV(file) {
  const formData = new FormData();
  formData.append('file', file);

  // Clear cache before upload so fresh data is fetched after
  clearCache();

  const result = await apiFetch('/upload-csv', {
    method: 'POST',
    body: formData,
  }, false); // Don't cache POST

  // Clear cache again after successful upload to force refresh
  if (result && !result.error) {
    clearCache();
  }

  return result;
}
