import { createContext, useContext, useState, useCallback, useMemo } from 'react'
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-react'

const ToastContext = createContext(null)

// Variants com cores e ícones
const variants = {
  success: {
    icon: CheckCircle,
    bg: 'bg-green-500/10',
    border: 'border-green-500/30',
    iconColor: 'text-green-400',
    textColor: 'text-green-300'
  },
  error: {
    icon: AlertCircle,
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    iconColor: 'text-red-400',
    textColor: 'text-red-300'
  },
  warning: {
    icon: AlertTriangle,
    bg: 'bg-yellow-500/10',
    border: 'border-yellow-500/30',
    iconColor: 'text-yellow-400',
    textColor: 'text-yellow-300'
  },
  info: {
    icon: Info,
    bg: 'bg-cyan-500/10',
    border: 'border-cyan-500/30',
    iconColor: 'text-cyan-400',
    textColor: 'text-cyan-300'
  }
}

function ToastItem({ id, message, type = 'info', onClose }) {
  const variant = variants[type] || variants.info
  const Icon = variant.icon

  return (
    <div
      className={`toast flex items-start gap-3 p-4 rounded-lg border ${variant.bg} ${variant.border} shadow-lg animate-slide-in`}
      style={{ minWidth: '300px', maxWidth: '400px' }}
      role="alert"
      aria-live="polite"
    >
      <Icon className={`w-5 h-5 ${variant.iconColor} flex-shrink-0 mt-0.5`} />
      <p className={`flex-1 text-sm ${variant.textColor}`}>{message}</p>
      <button
        onClick={() => onClose(id)}
        className="toast-close text-gray-500 hover:text-gray-300 transition-colors p-1"
        aria-label="Fechar notificação"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  )
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(toast => toast.id !== id))
  }, [])

  const addToast = useCallback((message, type = 'info', duration = 3000) => {
    const id = Date.now() + Math.random()
    setToasts(prev => [...prev, { id, message, type }])

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, duration)
    }

    return id
  }, [removeToast])

  // Memoize the toast object to prevent infinite re-renders
  const toast = useMemo(() => ({
    success: (message, duration) => addToast(message, 'success', duration),
    error: (message, duration) => addToast(message, 'error', duration),
    warning: (message, duration) => addToast(message, 'warning', duration),
    info: (message, duration) => addToast(message, 'info', duration),
    remove: removeToast
  }), [addToast, removeToast])

  return (
    <ToastContext.Provider value={toast}>
      {children}
      {/* Toast Container - responsivo */}
      <div className="toast-container fixed bottom-4 right-4 z-[9999] flex flex-col gap-2">
        {toasts.map(t => (
          <ToastItem
            key={t.id}
            id={t.id}
            message={t.message}
            type={t.type}
            onClose={removeToast}
          />
        ))}
      </div>
      <style>{`
        @keyframes slide-in {
          from {
            opacity: 0;
            transform: translateX(100%);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
        .animate-slide-in {
          animation: slide-in 0.3s ease-out;
        }
      `}</style>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}

export default ToastProvider
