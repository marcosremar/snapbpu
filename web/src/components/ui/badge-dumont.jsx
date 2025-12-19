/**
 * Badge Component - Adaptado do TailAdmin para Dumont Cloud
 * Paleta: Dark theme com accent verde (#4ade80, #22c55e)
 */

const Badge = ({
  variant = "light",
  color = "success",
  size = "md",
  startIcon,
  endIcon,
  children,
}) => {
  const baseStyles =
    "inline-flex items-center px-2.5 py-0.5 justify-center gap-1 rounded-full font-medium";

  const sizeStyles = {
    sm: "text-xs",
    md: "text-sm",
  };

  // Cores adaptadas para Dumont Cloud (dark theme)
  const variants = {
    light: {
      success: "bg-green-500/15 text-green-400 border border-green-500/30",
      error: "bg-red-500/15 text-red-400 border border-red-500/30",
      warning: "bg-yellow-500/15 text-yellow-400 border border-yellow-500/30",
      info: "bg-cyan-500/15 text-cyan-400 border border-cyan-500/30",
      primary: "bg-green-500/15 text-green-400 border border-green-500/30",
      secondary: "bg-gray-500/15 text-gray-400 border border-gray-500/30",
      online: "bg-green-500/20 text-green-400 border border-green-500/30",
      offline: "bg-gray-500/20 text-gray-400 border border-gray-500/30",
      hibernating: "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30",
    },
    solid: {
      success: "bg-green-500 text-white",
      error: "bg-red-500 text-white",
      warning: "bg-yellow-500 text-black",
      info: "bg-cyan-500 text-white",
      primary: "bg-green-500 text-white",
      secondary: "bg-gray-600 text-white",
      online: "bg-green-500 text-white",
      offline: "bg-gray-500 text-white",
      hibernating: "bg-yellow-500 text-black",
    },
  };

  const sizeClass = sizeStyles[size];
  const colorStyles = variants[variant][color] || variants[variant].primary;

  return (
    <span className={`${baseStyles} ${sizeClass} ${colorStyles}`}>
      {startIcon && <span className="mr-1">{startIcon}</span>}
      {children}
      {endIcon && <span className="ml-1">{endIcon}</span>}
    </span>
  );
};

// Status Badge específico para máquinas
export const StatusBadge = ({ status }) => {
  const statusMap = {
    running: { color: "online", label: "Online", icon: "●" },
    online: { color: "online", label: "Online", icon: "●" },
    stopped: { color: "offline", label: "Offline", icon: "○" },
    offline: { color: "offline", label: "Offline", icon: "○" },
    hibernating: { color: "hibernating", label: "Hibernando", icon: "◐" },
    starting: { color: "warning", label: "Iniciando", icon: "◔" },
    stopping: { color: "warning", label: "Parando", icon: "◔" },
  };

  const config = statusMap[status?.toLowerCase()] || statusMap.offline;

  return (
    <Badge color={config.color} size="sm">
      <span className="mr-1">{config.icon}</span>
      {config.label}
    </Badge>
  );
};

// Trend Badge para métricas (↑ 11% ou ↓ 5%)
export const TrendBadge = ({ value, inverted = false }) => {
  const isPositive = inverted ? value < 0 : value > 0;
  const color = isPositive ? "success" : "error";
  const arrow = value > 0 ? "↑" : "↓";

  return (
    <Badge color={color} size="sm">
      {arrow} {Math.abs(value)}%
    </Badge>
  );
};

export default Badge;
