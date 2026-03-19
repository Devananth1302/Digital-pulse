/**
 * Stat Badge Component - Display key metrics with glassmorphism
 */
import React from 'react';
import { cn } from '@/lib/utils';

interface StatBadgeProps {
  label: string;
  value: string | number;
  unit?: string;
  trend?: 'up' | 'down' | 'stable';
  color?: 'cyan' | 'purple' | 'pink' | 'green' | 'orange';
  variant?: 'cyan' | 'purple' | 'pink' | 'green' | 'orange';
  className?: string;
}

const colorMap = {
  cyan: 'from-cyan-400 to-blue-400',
  purple: 'from-purple-400 to-pink-400',
  pink: 'from-pink-400 to-red-400',
  green: 'from-green-400 to-emerald-400',
  orange: 'from-orange-400 to-yellow-400',
};

const trendArrows = {
  up: '↑',
  down: '↓',
  stable: '→',
};

const trendColors = {
  up: 'text-green-400',
  down: 'text-red-400',
  stable: 'text-yellow-400',
};

export const StatBadge = ({
  label,
  value,
  unit,
  trend,
  color = 'cyan',
  variant,
  className,
}: StatBadgeProps) => {
  // Use variant if provided, otherwise use color
  const finalColor = (variant || color) as 'cyan' | 'purple' | 'pink' | 'green' | 'orange';
  return (
    <div
      className={cn(
        'rounded-lg backdrop-blur-xl bg-white/5 border border-white/10 p-4 hover:bg-white/10 transition-colors',
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs uppercase tracking-widest text-gray-400 mb-2">{label}</p>
          <div className="flex items-baseline gap-2">
            <span className={cn('text-3xl font-bold bg-gradient-to-r bg-clip-text text-transparent', colorMap[finalColor])}>
              {value}
            </span>
            {unit && <span className="text-sm text-gray-400">{unit}</span>}
          </div>
        </div>
        {trend && <span className={cn('text-2xl', trendColors[trend])}>{trendArrows[trend]}</span>}
      </div>
    </div>
  );
};
