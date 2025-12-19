/**
 * MetricCard Component - Inspirado no EcommerceMetrics do TailAdmin
 * Adaptado para Dumont Cloud com paleta dark + verde
 */

import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

// Metric Card Principal (similar ao StatCard mas com mais opções)
export const MetricCard = ({
  icon: Icon,
  title,
  value,
  subtext,
  trend = null,
  trendLabel = "",
  color = "green",
  tooltip,
  animate = false,
  comparison,
  loading = false,
  onClick,
}) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const [displayValue, setDisplayValue] = useState(animate ? '0' : value);

  // Count-up animation
  useEffect(() => {
    if (!animate || typeof value !== 'string') return;

    const match = value.match(/^\$?([\d,]+)/);
    if (!match) {
      setDisplayValue(value);
      return;
    }

    const targetNum = parseInt(match[1].replace(/,/g, ''), 10);
    const prefix = value.startsWith('$') ? '$' : '';
    const suffix = value.replace(/^\$?[\d,]+/, '');
    const duration = 1500;
    const steps = 30;
    const stepDuration = duration / steps;
    let currentStep = 0;

    const timer = setInterval(() => {
      currentStep++;
      const progress = currentStep / steps;
      const easeOut = 1 - Math.pow(1 - progress, 3);
      const currentValue = Math.floor(targetNum * easeOut);
      setDisplayValue(`${prefix}${currentValue.toLocaleString()}${suffix}`);

      if (currentStep >= steps) {
        clearInterval(timer);
        setDisplayValue(value);
      }
    }, stepDuration);

    return () => clearInterval(timer);
  }, [animate, value]);

  const colorClasses = {
    green: {
      bg: 'from-green-500/20 to-green-600/10',
      border: 'border-green-500/30',
      icon: 'bg-green-500/20 text-green-400',
      text: 'text-green-400',
    },
    blue: {
      bg: 'from-blue-500/20 to-blue-600/10',
      border: 'border-blue-500/30',
      icon: 'bg-blue-500/20 text-blue-400',
      text: 'text-blue-400',
    },
    purple: {
      bg: 'from-purple-500/20 to-purple-600/10',
      border: 'border-purple-500/30',
      icon: 'bg-purple-500/20 text-purple-400',
      text: 'text-purple-400',
    },
    yellow: {
      bg: 'from-yellow-500/20 to-yellow-600/10',
      border: 'border-yellow-500/30',
      icon: 'bg-yellow-500/20 text-yellow-400',
      text: 'text-yellow-400',
    },
    red: {
      bg: 'from-red-500/20 to-red-600/10',
      border: 'border-red-500/30',
      icon: 'bg-red-500/20 text-red-400',
      text: 'text-red-400',
    },
    gray: {
      bg: 'from-gray-500/20 to-gray-600/10',
      border: 'border-gray-500/30',
      icon: 'bg-gray-500/20 text-gray-400',
      text: 'text-gray-400',
    },
  };

  const colors = colorClasses[color] || colorClasses.green;

  if (loading) {
    return (
      <div className={`
        p-5 rounded-2xl border bg-gradient-to-br backdrop-blur-sm
        ${colors.bg} ${colors.border}
        animate-pulse
      `}>
        <div className="h-12 w-12 rounded-xl bg-gray-700/50 mb-4" />
        <div className="h-4 w-20 bg-gray-700/50 rounded mb-2" />
        <div className="h-8 w-32 bg-gray-700/50 rounded" />
      </div>
    );
  }

  return (
    <div
      className={`
        p-5 rounded-2xl border bg-gradient-to-br backdrop-blur-sm relative
        ${colors.bg} ${colors.border}
        ${onClick ? 'cursor-pointer hover:scale-[1.02] transition-transform' : ''}
      `}
      onClick={onClick}
      onMouseEnter={() => tooltip && setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      {/* Tooltip */}
      {tooltip && showTooltip && (
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-xs text-gray-300 whitespace-nowrap z-50 shadow-lg">
          {tooltip}
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
        </div>
      )}

      {/* Icon */}
      {Icon && (
        <div className={`flex items-center justify-center w-12 h-12 rounded-xl mb-4 ${colors.icon}`}>
          <Icon size={24} />
        </div>
      )}

      {/* Content */}
      <div className="flex items-end justify-between">
        <div>
          <span className="text-sm text-gray-400">{title}</span>
          <h4 className="mt-1 text-2xl font-bold text-white">
            {animate ? displayValue : value}
          </h4>
          {subtext && (
            <span className="text-xs text-gray-500 mt-1 block">{subtext}</span>
          )}
          {comparison && (
            <span className={`text-xs mt-1 block ${colors.text}`}>{comparison}</span>
          )}
        </div>

        {/* Trend Badge */}
        {trend !== null && (
          <div className={`
            flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium
            ${trend >= 0 ? 'bg-green-500/15 text-green-400' : 'bg-red-500/15 text-red-400'}
          `}>
            {trend >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            {Math.abs(trend)}%
            {trendLabel && <span className="text-gray-500 ml-1">{trendLabel}</span>}
          </div>
        )}
      </div>
    </div>
  );
};

// Grid de Métricas
export const MetricsGrid = ({ children, columns = 4 }) => {
  const colClasses = {
    2: 'grid-cols-1 sm:grid-cols-2',
    3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-2 md:grid-cols-4',
  };

  return (
    <div className={`grid gap-4 md:gap-6 ${colClasses[columns] || colClasses[4]}`}>
      {children}
    </div>
  );
};

// Mini Metric (para usar inline ou em cards menores)
export const MiniMetric = ({ label, value, trend, color = "green" }) => {
  const colorClass = {
    green: "text-green-400",
    blue: "text-blue-400",
    yellow: "text-yellow-400",
    red: "text-red-400",
    gray: "text-gray-400",
  };

  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-gray-400">{label}</span>
      <div className="flex items-center gap-2">
        <span className={`font-semibold ${colorClass[color]}`}>{value}</span>
        {trend !== undefined && (
          <span className={`text-xs ${trend >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {trend >= 0 ? '↑' : '↓'}{Math.abs(trend)}%
          </span>
        )}
      </div>
    </div>
  );
};

export default MetricCard;
