/**
 * Dynamic AI Insight Generator
 * Transforms raw data into actionable, topic-aware insights
 */

// Topic extraction keywords for categorization
const TOPIC_CATEGORIES = {
  technology: ['tech', 'ai', 'software', 'app', 'digital', 'cyber', 'data', 'cloud', 'startup', 'innovation', 'google', 'apple', 'microsoft', 'meta', 'amazon'],
  politics: ['election', 'government', 'policy', 'minister', 'parliament', 'vote', 'political', 'democracy', 'law', 'court', 'trump', 'biden', 'modi'],
  finance: ['market', 'stock', 'economy', 'bank', 'investment', 'crypto', 'bitcoin', 'inflation', 'gdp', 'trade', 'finance', 'dollar', 'rupee'],
  health: ['health', 'covid', 'vaccine', 'hospital', 'medical', 'disease', 'treatment', 'drug', 'wellness', 'mental', 'doctor'],
  sports: ['cricket', 'football', 'sports', 'match', 'tournament', 'league', 'player', 'team', 'championship', 'olympics', 'ipl'],
  entertainment: ['movie', 'film', 'music', 'celebrity', 'bollywood', 'hollywood', 'actor', 'singer', 'concert', 'show', 'netflix'],
  education: ['education', 'school', 'university', 'student', 'exam', 'learning', 'course', 'college', 'teacher', 'edtech'],
  environment: ['climate', 'environment', 'pollution', 'green', 'sustainable', 'carbon', 'renewable', 'energy', 'weather', 'disaster'],
};

// Dynamic insight patterns based on metrics
const INSIGHT_PATTERNS = {
  explosive_growth: {
    thresholds: { growthRate: 3.0, engagement: 5000 },
    templates: [
      (topic, growth) => `${topic} is experiencing explosive growth (+${growth}%) - this could dominate discourse within hours.`,
      (topic, growth) => `Unprecedented ${growth}% surge in ${topic} discussions signals a potential viral moment.`,
      (topic, growth) => `${topic} has crossed viral threshold with ${growth}% acceleration.`,
    ],
  },
  rapid_growth: {
    thresholds: { growthRate: 2.0, engagement: 2000 },
    templates: [
      (topic, growth) => `${topic} gaining strong momentum (+${growth}%) - expect significant visibility increase.`,
      (topic, growth) => `Rising interest in ${topic} shows ${growth}% growth trajectory.`,
    ],
  },
  steady_growth: {
    thresholds: { growthRate: 1.5, engagement: 500 },
    templates: [
      (topic, growth) => `${topic} showing consistent engagement growth of ${growth}%.`,
      (topic) => `Sustained interest building around ${topic} discussions.`,
    ],
  },
  declining: {
    thresholds: { growthRate: 0.8 },
    templates: [
      (topic) => `${topic} engagement declining - audience attention shifting elsewhere.`,
      (topic) => `Interest in ${topic} waning - consider pivoting to related emerging topics.`,
    ],
  },
};

/**
 * Extract topic category from title/content
 */
function extractTopicCategory(text) {
  if (!text) return { category: 'general', keywords: [] };

  const lowerText = text.toLowerCase();
  const matchedKeywords = [];
  let matchedCategory = 'general';
  let maxMatches = 0;

  for (const [category, keywords] of Object.entries(TOPIC_CATEGORIES)) {
    const matches = keywords.filter(kw => lowerText.includes(kw));
    if (matches.length > maxMatches) {
      maxMatches = matches.length;
      matchedCategory = category;
      matchedKeywords.push(...matches);
    }
  }

  return { category: matchedCategory, keywords: matchedKeywords.slice(0, 3) };
}

/**
 * Extract key entities/subjects from title
 */
function extractSubject(title) {
  if (!title) return 'This topic';

  // Clean and extract meaningful subject
  const cleaned = title
    .replace(/^(breaking|urgent|exclusive|just in):\s*/i, '')
    .replace(/\s*\|\s*.+$/, '')
    .replace(/\s*-\s*.+$/, '');

  // Get first meaningful phrase (up to 6 words)
  const words = cleaned.split(/\s+/).slice(0, 6);
  if (words.length < 2) return 'This narrative';

  return words.join(' ');
}

/**
 * Calculate time to peak estimate
 */
function estimateTimeToPeak(growthRate, currentEngagement) {
  if (growthRate > 3) return '2-4 hours';
  if (growthRate > 2) return '4-8 hours';
  if (growthRate > 1.5) return '8-16 hours';
  if (currentEngagement > 10000) return '12-24 hours';
  return '24-48 hours';
}

/**
 * Determine urgency level
 */
function determineUrgency(data) {
  const { growthRate = 1, severity = 'low', virality = 0, engagement = 0 } = data;

  if (severity === 'high' || growthRate > 3 || virality > 50) return 'high';
  if (severity === 'medium' || growthRate > 2 || virality > 30) return 'medium';
  return 'low';
}

/**
 * Generate dynamic "why this matters" explanation
 */
function generateWhyThisMatters(topicInfo, metrics) {
  const { category } = topicInfo;
  const { growthRate = 1, engagement = 0 } = metrics;

  const categoryReasons = {
    technology: 'Tech narratives often drive market movements and influence industry decisions.',
    politics: 'Political discourse can rapidly shift public opinion and policy agendas.',
    finance: 'Financial narratives directly impact market sentiment and investment behavior.',
    health: 'Health-related narratives significantly influence public behavior and policy.',
    sports: 'Sports narratives drive massive engagement and brand visibility opportunities.',
    entertainment: 'Entertainment trends shape cultural conversations and consumer preferences.',
    education: 'Education narratives influence policy decisions and institutional strategies.',
    environment: 'Environmental topics increasingly drive regulatory and corporate action.',
    general: 'Cross-domain narratives often signal broader cultural shifts.',
  };

  let reason = categoryReasons[category] || categoryReasons.general;

  if (growthRate > 2) {
    reason += ' The rapid growth suggests this may become a dominant talking point.';
  }
  if (engagement > 5000) {
    reason += ' High engagement indicates strong audience resonance.';
  }

  return reason;
}

/**
 * Generate insight for Pulse Score data
 */
export function generatePulseInsight(pulseData) {
  if (!pulseData) return null;

  const score = pulseData.score ?? 0;
  const trend = pulseData.trend_direction || 'stable';
  const signals = pulseData.meta?.signals_detected ?? 0;
  const clusters = pulseData.meta?.active_clusters ?? 0;

  // Dynamic insight based on actual metrics
  let insight, impact, action;

  if (score >= 70) {
    insight = `High cultural activity detected: ${signals} active signals across ${clusters} narrative clusters.`;
    impact = 'Multiple narratives competing for attention - critical monitoring window.';
    action = signals > 5
      ? 'Prioritize high-severity signals for immediate response.'
      : 'Review emerging patterns for strategic positioning.';
  } else if (score >= 40) {
    insight = `Moderate activity with ${signals} signals tracking across ${clusters} clusters.`;
    impact = 'Selective narratives gaining traction - opportunity window open.';
    action = 'Identify top-performing narratives for potential amplification.';
  } else {
    insight = `Low activity period: ${clusters} clusters with minimal signal activity.`;
    impact = 'Stable landscape - no urgent attention required.';
    action = 'Good time for strategic content planning and competitive analysis.';
  }

  // Add trend context
  if (trend === 'rising') {
    insight += ' Activity trending upward.';
  } else if (trend === 'falling') {
    insight += ' Activity cooling from recent peak.';
  }

  const urgency = score >= 70 ? 'high' : score >= 40 ? 'medium' : 'low';

  return {
    title: 'Cultural Pulse',
    value: Math.round(score),
    trend,
    insight,
    impact,
    action,
    confidence: calculateConfidence([score > 0, signals > 0, clusters > 0, !!trend]),
    context: `Monitoring ${clusters} clusters | ${signals} signals detected`,
    severity: urgency,
    urgency,
    whyThisMatters: score >= 50
      ? 'Elevated activity often precedes significant narrative shifts that can impact brand perception.'
      : 'Stable periods provide opportunities for proactive narrative shaping.',
  };
}

/**
 * Generate insight for Emerging Signal
 */
export function generateSignalInsight(signal) {
  if (!signal) return null;

  const growthRate = signal.growth_rate ?? 1;
  const severity = signal.severity || 'low';
  const growthPct = Math.round((growthRate - 1) * 100);
  const topic = signal.topic || 'Unknown Topic';

  // Extract topic context
  const topicInfo = extractTopicCategory(topic);
  const subject = extractSubject(topic);

  // Dynamic pattern matching
  let pattern;
  if (growthRate > 3) pattern = INSIGHT_PATTERNS.explosive_growth;
  else if (growthRate > 2) pattern = INSIGHT_PATTERNS.rapid_growth;
  else if (growthRate > 1.5) pattern = INSIGHT_PATTERNS.steady_growth;
  else pattern = INSIGHT_PATTERNS.declining;

  // Select template based on data
  const templateFn = pattern.templates[Math.floor(Math.random() * pattern.templates.length)];
  const insight = templateFn(subject, growthPct);

  // Generate dynamic impact
  let impact;
  if (severity === 'high') {
    impact = `Could dominate ${topicInfo.category} discourse within hours. Peak expected in ${estimateTimeToPeak(growthRate, signal.current_engagement)}.`;
  } else if (severity === 'medium') {
    impact = `Building momentum in ${topicInfo.category} space. Monitor for acceleration.`;
  } else {
    impact = `Early-stage signal - too early to assess full impact trajectory.`;
  }

  // Dynamic action
  let action;
  if (growthRate > 2.5) {
    action = 'Immediate attention required. Prepare response or engagement strategy.';
  } else if (growthRate > 1.5) {
    action = 'Add to active watchlist. Prepare talking points and monitor for escalation.';
  } else {
    action = 'Continue passive monitoring. No immediate action needed.';
  }

  return {
    title: topic,
    value: `+${growthPct}%`,
    trend: 'rising',
    insight,
    impact,
    action,
    confidence: calculateConfidence([growthRate > 1, signal.current_engagement > 0, !!topic]),
    context: `${topicInfo.category.toUpperCase()} | Current: ${Math.round(signal.current_engagement || 0)} | Previous: ${Math.round(signal.previous_engagement || 0)}`,
    severity,
    urgency: determineUrgency({ growthRate, severity }),
    timeToPeak: estimateTimeToPeak(growthRate, signal.current_engagement),
    whyThisMatters: generateWhyThisMatters(topicInfo, { growthRate, engagement: signal.current_engagement }),
    topicCategory: topicInfo.category,
    keywords: topicInfo.keywords,
  };
}

/**
 * Generate insight for Forecast
 */
export function generateForecastInsight(forecast) {
  if (!forecast) return null;

  const trend = forecast.trend_prediction || 'stable';
  const confidence_score = forecast.confidence_score ?? 0;
  const predicted = forecast.predicted_engagement ?? 0;
  const topic = forecast.topic || 'General';

  const topicInfo = extractTopicCategory(topic);
  const subject = extractSubject(topic);

  let insight, impact, action;

  if (trend === 'rising') {
    const multiplier = Math.round((predicted / (forecast.current_engagement || predicted)) * 100 - 100);
    insight = `${subject} predicted to surge ${multiplier > 0 ? `+${multiplier}%` : ''} over next 48 hours based on engagement velocity.`;
    impact = `Topic likely to gain significant visibility in ${topicInfo.category} space.`;
    action = 'Position early for maximum impact. Consider proactive content creation.';
  } else if (trend === 'falling') {
    insight = `${subject} shows declining trajectory - engagement expected to decrease.`;
    impact = `Reduced relevance predicted - audience attention shifting to other ${topicInfo.category} topics.`;
    action = 'Deprioritize resources. Identify emerging alternatives in this space.';
  } else {
    insight = `${subject} expected to maintain steady engagement levels.`;
    impact = `Reliable baseline in ${topicInfo.category} - no major disruptions anticipated.`;
    action = 'Maintain current strategy. Monitor for unexpected shifts.';
  }

  return {
    title: topic,
    value: trend === 'rising' ? '▲ Up' : trend === 'falling' ? '▼ Down' : '● Stable',
    trend,
    insight,
    impact,
    action,
    confidence: confidence_score >= 0.8 ? 'high' : confidence_score >= 0.5 ? 'medium' : 'low',
    context: `Projected: ${Math.round(predicted).toLocaleString()} engagements | Confidence: ${Math.round(confidence_score * 100)}%`,
    severity: trend === 'rising' ? 'high' : trend === 'falling' ? 'low' : 'medium',
    urgency: trend === 'rising' && confidence_score > 0.7 ? 'medium' : 'low',
    timeToPeak: trend === 'rising' ? '24-48 hours' : null,
    whyThisMatters: generateWhyThisMatters(topicInfo, { engagement: predicted }),
  };
}

/**
 * Generate insight for Narrative/Post
 */
export function generateNarrativeInsight(post) {
  if (!post) return null;

  const virality = post.virality_score ?? 0;
  const engagement = post.engagement_total ?? 0;
  const title = post.title || '';
  const velocity = post.engagement_velocity ?? 0;

  const topicInfo = extractTopicCategory(title);
  const subject = extractSubject(title);

  let category, insight, impact, action;

  if (virality >= 30) {
    category = 'viral';
    insight = `"${subject.substring(0, 40)}${subject.length > 40 ? '...' : ''}" is achieving viral status with ${virality.toFixed(1)} virality score.`;
    impact = `Strong shareability in ${topicInfo.category} - potential for significant amplification.`;
    action = 'Leverage momentum. Consider related content or engagement strategy.';
  } else if (virality >= 15) {
    category = 'trending';
    insight = `${subject.substring(0, 40)} gaining above-average traction (${virality.toFixed(1)} virality).`;
    impact = `Growing audience interest in ${topicInfo.category} space - opportunity window active.`;
    action = 'Monitor trajectory. Consider amplification if aligned with strategy.';
  } else {
    category = 'standard';
    insight = `${subject.substring(0, 40)} showing typical engagement for ${topicInfo.category} content.`;
    impact = 'Normal visibility - no unusual activity patterns detected.';
    action = 'Continue standard monitoring. No immediate action required.';
  }

  // Add velocity context
  if (velocity > 100) {
    insight += ` High velocity (${velocity.toFixed(0)}/hr) indicates rapid spread.`;
  }

  return {
    title: title.substring(0, 60),
    value: virality.toFixed(1),
    trend: virality >= 20 ? 'rising' : virality >= 10 ? 'stable' : 'falling',
    insight,
    impact,
    action,
    confidence: calculateConfidence([virality > 0, engagement > 0, !!title]),
    context: `${engagement.toLocaleString()} engagements | ${velocity.toFixed(1)}/hr velocity | ${topicInfo.category}`,
    severity: category === 'viral' ? 'high' : category === 'trending' ? 'medium' : 'low',
    urgency: determineUrgency({ virality, engagement }),
    whyThisMatters: generateWhyThisMatters(topicInfo, { engagement }),
    topicCategory: topicInfo.category,
    keywords: topicInfo.keywords,
  };
}

/**
 * Generate overall dashboard summary insight
 */
export function generateDashboardSummary(pulseData, narratives, emerging, forecasts) {
  const posts = narratives?.posts || [];
  const signals = emerging?.signals || [];
  const forecastList = forecasts?.forecasts || [];
  const score = pulseData?.score ?? 0;

  // Count significant items
  const highSignals = signals.filter(s => s.severity === 'high').length;
  const mediumSignals = signals.filter(s => s.severity === 'medium').length;
  const risingForecasts = forecastList.filter(f => f.trend_prediction === 'rising').length;
  const viralPosts = posts.filter(p => (p.virality_score ?? 0) >= 30).length;
  const trendingPosts = posts.filter(p => (p.virality_score ?? 0) >= 15 && (p.virality_score ?? 0) < 30).length;

  // Determine overall status with nuance
  let status = 'stable';
  let urgency = 'low';
  let recommendation;

  if (highSignals > 0) {
    status = 'critical';
    urgency = 'high';
    recommendation = `${highSignals} high-priority signal${highSignals > 1 ? 's' : ''} require immediate review.`;
  } else if (score >= 70 || viralPosts > 2) {
    status = 'active';
    urgency = 'high';
    recommendation = 'High activity period - monitor top narratives closely.';
  } else if (mediumSignals > 2 || risingForecasts > 2 || score >= 50) {
    status = 'emerging';
    urgency = 'medium';
    recommendation = 'Multiple emerging patterns detected. Review for opportunities.';
  } else {
    status = 'stable';
    urgency = 'low';
    recommendation = 'Landscape stable. Good time for strategic planning.';
  }

  // Build dynamic summary
  const summaryParts = [];
  if (highSignals > 0) summaryParts.push(`${highSignals} critical signal${highSignals > 1 ? 's' : ''}`);
  if (viralPosts > 0) summaryParts.push(`${viralPosts} viral narrative${viralPosts > 1 ? 's' : ''}`);
  if (trendingPosts > 0) summaryParts.push(`${trendingPosts} trending`);
  if (risingForecasts > 0) summaryParts.push(`${risingForecasts} rising forecast${risingForecasts > 1 ? 's' : ''}`);

  // Extract top topics
  const topTopics = posts.slice(0, 5).map(p => extractTopicCategory(p.title).category);
  const dominantCategory = topTopics.length > 0
    ? [...new Set(topTopics)].slice(0, 2).join(', ')
    : 'general';

  return {
    status,
    urgency,
    score: Math.round(score),
    summary: summaryParts.length > 0
      ? summaryParts.join(' • ')
      : 'No critical items requiring immediate attention.',
    recommendation,
    dominantCategories: dominantCategory,
    metrics: {
      totalPosts: posts.length,
      totalSignals: signals.length,
      highPriorityCount: highSignals,
      viralCount: viralPosts,
    },
  };
}

/**
 * Helper: Calculate confidence level from boolean checks
 */
function calculateConfidence(checks) {
  const passed = checks.filter(Boolean).length;
  const ratio = passed / checks.length;
  if (ratio >= 0.75) return 'high';
  if (ratio >= 0.5) return 'medium';
  return 'low';
}

/**
 * Get color for confidence level
 */
export function getConfidenceColor(confidence) {
  switch (confidence) {
    case 'high': return '#00c853';
    case 'medium': return '#ff9f43';
    case 'low': return '#ff3d8e';
    default: return '#6b7280';
  }
}

/**
 * Get color for severity/urgency
 */
export function getSeverityColor(severity) {
  switch (severity) {
    case 'high': return '#ff3d8e';
    case 'medium': return '#ff9f43';
    case 'low': return '#00c853';
    default: return '#00d4ff';
  }
}
