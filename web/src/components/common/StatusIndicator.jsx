import { StatusBadge } from '../ui/dumont-ui'

/**
 * StatusIndicator - Consolidated status display component
 * Provides multiple variants for displaying machine/instance status
 * Ensures consistency across the application
 */
export const StatusIndicator = ({ status, variant = 'badge', showLabel = true }) => {
  const statusColors = {
    running: { dot: 'bg-green-400', label: 'Rodando', text: 'text-green-400' },
    stopped: { dot: 'bg-gray-400', label: 'Parado', text: 'text-gray-400' },
    hibernating: { dot: 'bg-yellow-400', label: 'Hibernando', text: 'text-yellow-400' },
    paused: { dot: 'bg-cyan-400', label: 'Pausado', text: 'text-cyan-400' },
    error: { dot: 'bg-red-400', label: 'Erro', text: 'text-red-400' },
    starting: { dot: 'bg-green-400', label: 'Iniciando', text: 'text-green-400' },
    stopping: { dot: 'bg-yellow-400', label: 'Parando', text: 'text-yellow-400' },
  }

  const colors = statusColors[status] || statusColors.stopped

  const variants = {
    badge: <StatusBadge status={status} />,
    dot: (
      <div className="flex items-center gap-2">
        <div className={`w-2.5 h-2.5 rounded-full ${colors.dot}`} />
        {showLabel && <span className={`text-xs ${colors.text}`}>{colors.label}</span>}
      </div>
    ),
    label: (
      <span className={`text-sm font-medium ${colors.text}`}>
        {colors.label}
      </span>
    ),
    pill: (
      <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${colors.text} bg-opacity-10`}
        style={{ backgroundColor: colors.dot.replace('bg-', 'rgba(').replace('-400', ', 0.1)') }}>
        <div className={`w-2 h-2 rounded-full ${colors.dot}`} />
        {colors.label}
      </div>
    ),
  }

  return variants[variant] || variants.badge
}

export default StatusIndicator
