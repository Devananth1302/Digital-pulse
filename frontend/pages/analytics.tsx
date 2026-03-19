'use client';

/**
 * Analytics Dashboard Page
 * Demo integration of TrendingDashboard component
 */

import { TrendingDashboard } from '@/components/TrendingDashboard';

export default function AnalyticsPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-black p-4 md:p-8">
      {/* Background animation */}
      <div className="fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse animation-delay-2000" />
      </div>

      <div className="max-w-7xl mx-auto">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-5xl md:text-6xl font-bold mb-2">
            <span className="bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent">
              Digital Pulse
            </span>
          </h1>
          <p className="text-gray-400 text-lg">Real-time Social Analytics Engine</p>
        </div>

        {/* Dashboard Content */}
        <TrendingDashboard />
      </div>
    </div>
  );
}
