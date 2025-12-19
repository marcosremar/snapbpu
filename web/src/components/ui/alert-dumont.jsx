/**
 * Alert Component - Adaptado do TailAdmin para Dumont Cloud
 * Paleta: Dark theme com accent verde (#4ade80, #22c55e)
 */

import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';

const Alert = ({
  variant = "info",
  title,
  message,
  showLink = false,
  linkHref = "#",
  linkText = "Saiba mais",
  dismissible = false,
  onDismiss,
  children,
}) => {
  // Cores adaptadas para Dumont Cloud (dark theme)
  const variantClasses = {
    success: {
      container: "border-green-500/30 bg-green-500/10",
      icon: "text-green-400",
      title: "text-green-400",
    },
    error: {
      container: "border-red-500/30 bg-red-500/10",
      icon: "text-red-400",
      title: "text-red-400",
    },
    warning: {
      container: "border-yellow-500/30 bg-yellow-500/10",
      icon: "text-yellow-400",
      title: "text-yellow-400",
    },
    info: {
      container: "border-blue-500/30 bg-blue-500/10",
      icon: "text-blue-400",
      title: "text-blue-400",
    },
  };

  const icons = {
    success: CheckCircle,
    error: XCircle,
    warning: AlertTriangle,
    info: Info,
  };

  const Icon = icons[variant];
  const styles = variantClasses[variant];

  return (
    <div className={`rounded-xl border p-4 ${styles.container}`}>
      <div className="flex items-start gap-3">
        <div className={`mt-0.5 ${styles.icon}`}>
          <Icon size={20} />
        </div>

        <div className="flex-1">
          {title && (
            <h4 className={`mb-1 text-sm font-semibold ${styles.title}`}>
              {title}
            </h4>
          )}

          {message && (
            <p className="text-sm text-gray-400">{message}</p>
          )}

          {children}

          {showLink && (
            <a
              href={linkHref}
              className="inline-block mt-3 text-sm font-medium text-gray-400 underline hover:text-white transition-colors"
            >
              {linkText}
            </a>
          )}
        </div>

        {dismissible && onDismiss && (
          <button
            onClick={onDismiss}
            className="text-gray-500 hover:text-white transition-colors"
          >
            <X size={18} />
          </button>
        )}
      </div>
    </div>
  );
};

// Alert inline (mais compacto)
export const AlertInline = ({ variant = "info", children }) => {
  const colors = {
    success: "text-green-400",
    error: "text-red-400",
    warning: "text-yellow-400",
    info: "text-blue-400",
  };

  const icons = {
    success: CheckCircle,
    error: XCircle,
    warning: AlertTriangle,
    info: Info,
  };

  const Icon = icons[variant];

  return (
    <div className={`flex items-center gap-2 text-sm ${colors[variant]}`}>
      <Icon size={16} />
      <span>{children}</span>
    </div>
  );
};

// Toast-style Alert (para notificações)
export const ToastAlert = ({ variant = "success", title, message, onClose }) => {
  const variantClasses = {
    success: "border-green-500/50 bg-[#131713]",
    error: "border-red-500/50 bg-[#131713]",
    warning: "border-yellow-500/50 bg-[#131713]",
    info: "border-blue-500/50 bg-[#131713]",
  };

  const iconColors = {
    success: "text-green-400",
    error: "text-red-400",
    warning: "text-yellow-400",
    info: "text-blue-400",
  };

  const icons = {
    success: CheckCircle,
    error: XCircle,
    warning: AlertTriangle,
    info: Info,
  };

  const Icon = icons[variant];

  return (
    <div className={`
      fixed bottom-4 right-4 z-50
      flex items-start gap-3 p-4
      rounded-xl border shadow-lg
      animate-slide-up
      ${variantClasses[variant]}
    `}>
      <Icon size={20} className={iconColors[variant]} />
      <div className="flex-1">
        {title && <p className="font-medium text-white text-sm">{title}</p>}
        {message && <p className="text-gray-400 text-sm">{message}</p>}
      </div>
      {onClose && (
        <button onClick={onClose} className="text-gray-500 hover:text-white">
          <X size={18} />
        </button>
      )}
    </div>
  );
};

export default Alert;
