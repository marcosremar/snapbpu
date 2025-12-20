import React, { useState, useEffect, useCallback, useRef } from 'react';
import { ChevronRight, TrendingUp, TrendingDown, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

// Page Header with Breadcrumb
export function PageHeader({ title, subtitle, breadcrumbs = [], actions }) {
  return (
    <div className="mb-6">
      {breadcrumbs.length > 0 && (
        <nav className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 mb-3">
          {breadcrumbs.map((item, index) => (
            <span key={index} className="flex items-center gap-2">
              {index > 0 && <ChevronRight size={14} className="text-gray-300 dark:text-gray-600" />}
              {item.href ? (
                <Link to={item.href} className="hover:text-brand-500 transition-colors">
                  {item.label}
                </Link>
              ) : (
                <span className="text-gray-900 dark:text-white font-medium">{item.label}</span>
              )}
            </span>
          ))}
        </nav>
      )}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">{title}</h1>
          {subtitle && <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{subtitle}</p>}
        </div>
        {actions && <div className="flex items-center gap-3">{actions}</div>}
      </div>
    </div>
  );
}

// Stat Card
export function StatCard({
  title,
  value,
  change,
  changeType = 'up',
  icon: Icon,
  iconColor = 'primary',
  subtitle,
  onClick,
  loading = false,
  emptyText = '---'
}) {
  const iconColorClasses = {
    primary: 'bg-gradient-to-br from-brand-50 to-brand-100 text-brand-500 dark:from-brand-500/10 dark:to-brand-500/20 dark:text-brand-400',
    success: 'bg-gradient-to-br from-success-50 to-success-100 text-success-500 dark:from-success-500/10 dark:to-success-500/20 dark:text-success-400',
    warning: 'bg-gradient-to-br from-warning-50 to-warning-100 text-warning-500 dark:from-warning-500/10 dark:to-warning-500/20 dark:text-warning-400',
    error: 'bg-gradient-to-br from-error-50 to-error-100 text-error-500 dark:from-error-500/10 dark:to-error-500/20 dark:text-error-400',
    gray: 'bg-gradient-to-br from-gray-100 to-gray-200 text-gray-500 dark:from-gray-800 dark:to-gray-700 dark:text-gray-400',
  };

  // Detect empty state
  const isEmpty = !loading && (value === null || value === undefined || value === '' || value === '0' || value === '$0' || value === '0/0');
  const displayValue = isEmpty ? emptyText : value;

  return (
    <div
      className={`bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 shadow-sm hover:shadow-md transition-all duration-200 ${onClick ? 'cursor-pointer hover:border-brand-300 dark:hover:border-brand-700 hover:-translate-y-0.5' : ''} ${loading ? 'animate-pulse' : ''}`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">{title}</p>
          {loading ? (
            <div className="h-8 bg-gray-200 dark:bg-gray-800 rounded animate-pulse w-24" />
          ) : (
            <p className={`text-2xl font-bold transition-colors ${isEmpty ? 'text-gray-400 dark:text-gray-600' : 'text-gray-900 dark:text-white'}`}>
              {displayValue}
            </p>
          )}
          {subtitle && !loading && (
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1.5">{subtitle}</p>
          )}
          {change && !loading && !isEmpty && (
            <div className={`flex items-center gap-1 mt-2.5 text-xs font-medium ${changeType === 'up' ? 'text-success-500' : 'text-error-500'}`}>
              {changeType === 'up' ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
              <span>{change}</span>
            </div>
          )}
        </div>
        {Icon && (
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm ${iconColorClasses[iconColor]}`}>
            <Icon size={24} className={loading ? 'animate-pulse' : ''} />
          </div>
        )}
      </div>
    </div>
  );
}

// Card Component - Dark theme by default
export function Card({ children, className = '', header, footer, noPadding = false }) {
  return (
    <div className={`bg-[#111411] rounded-xl border border-white/10 shadow-xl ${className}`}>
      {header && (
        <div className="px-6 py-4 border-b border-white/10">
          {typeof header === 'string' ? (
            <h3 className="text-lg font-semibold text-white">{header}</h3>
          ) : header}
        </div>
      )}
      <div className={noPadding ? '' : 'p-6'}>{children}</div>
      {footer && (
        <div className="px-6 py-4 border-t border-white/10 bg-white/5 rounded-b-xl">
          {footer}
        </div>
      )}
    </div>
  );
}

// Card Sub-components (for compatibility with old UI structure)
export function CardHeader({ children, className = '' }) {
  return (
    <div className={`px-6 py-4 border-b border-white/10 ${className}`}>
      {children}
    </div>
  );
}

export function CardTitle({ children, className = '' }) {
  return (
    <h3 className={`text-lg font-semibold text-white ${className}`}>
      {children}
    </h3>
  );
}

export function CardDescription({ children, className = '' }) {
  return (
    <p className={`text-sm text-gray-400 mt-1 ${className}`}>
      {children}
    </p>
  );
}

export function CardContent({ children, className = '' }) {
  return <div className={`p-6 ${className}`}>{children}</div>;
}

export function CardFooter({ children, className = '' }) {
  return (
    <div className={`px-6 py-4 border-t border-white/10 bg-white/5 rounded-b-xl ${className}`}>
      {children}
    </div>
  );
}

// Button Component
export function Button({
  children,
  variant = 'primary',
  size = 'md',
  icon: Icon,
  iconPosition = 'left',
  loading = false,
  disabled = false,
  className = '',
  ...props
}) {
  const variants = {
    primary: 'bg-emerald-300 text-gray-900 hover:bg-emerald-400 focus:ring-emerald-300 font-semibold shadow-lg shadow-emerald-500/20',
    secondary: 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-white/10 dark:text-gray-300 dark:hover:bg-white/20',
    success: 'bg-success-500 text-white hover:bg-success-600 focus:ring-success-500',
    error: 'bg-error-500 text-white hover:bg-error-600 focus:ring-error-500',
    warning: 'bg-warning-500 text-white hover:bg-warning-600 focus:ring-warning-500',
    outline: 'border border-gray-300 bg-transparent text-gray-700 hover:bg-gray-50 dark:border-white/20 dark:text-gray-300 dark:hover:bg-white/10',
    ghost: 'bg-transparent text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-white/10',
  };

  const sizes = {
    sm: 'px-4 py-2 text-xs',
    md: 'px-5 py-3 text-sm',
    lg: 'px-8 py-4 text-base',
  };

  return (
    <button
      className={`inline-flex items-center justify-center gap-2.5 font-medium rounded-xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
      )}
      {Icon && iconPosition === 'left' && !loading && <Icon size={size === 'sm' ? 14 : size === 'lg' ? 20 : 16} />}
      {children}
      {Icon && iconPosition === 'right' && !loading && <Icon size={size === 'sm' ? 14 : size === 'lg' ? 20 : 16} />}
    </button>
  );
}

// Badge Component
export function Badge({ children, variant = 'gray', size = 'md', dot = false }) {
  const variants = {
    primary: 'bg-brand-50 text-brand-700 dark:bg-brand-500/10 dark:text-brand-400',
    success: 'bg-success-50 text-success-700 dark:bg-success-500/10 dark:text-success-400',
    warning: 'bg-warning-50 text-warning-700 dark:bg-warning-500/10 dark:text-warning-400',
    error: 'bg-error-50 text-error-700 dark:bg-error-500/10 dark:text-error-400',
    gray: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  };

  const sizes = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-0.5 text-xs',
    lg: 'px-3 py-1 text-sm',
  };

  const dotColors = {
    primary: 'bg-brand-500',
    success: 'bg-success-500',
    warning: 'bg-warning-500',
    error: 'bg-error-500',
    gray: 'bg-gray-500',
  };

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-medium ${variants[variant]} ${sizes[size]}`}>
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${dotColors[variant]}`} />}
      {children}
    </span>
  );
}

// Table Component
export function Table({ columns, data, onRowClick, emptyMessage = 'Nenhum dado encontrado' }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            {columns.map((col, i) => (
              <th
                key={i}
                className={`px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider ${col.className || ''}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-12 text-center text-gray-500 dark:text-gray-400">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, rowIndex) => (
              <tr
                key={rowIndex}
                className={`border-b border-gray-200 dark:border-gray-800 ${onRowClick ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50' : ''} transition-colors`}
                onClick={() => onRowClick?.(row)}
              >
                {columns.map((col, colIndex) => (
                  <td key={colIndex} className={`px-4 py-4 text-sm text-gray-900 dark:text-gray-100 ${col.cellClassName || ''}`}>
                    {col.render ? col.render(row[col.accessor], row) : row[col.accessor]}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

// Input Component
export function Input({ label, error, helper, icon: Icon, className = '', ...props }) {
  return (
    <div className={className}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          {label}
        </label>
      )}
      <div className="relative">
        {Icon && (
          <div className="absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none">
            <Icon size={20} className="text-gray-400 dark:text-gray-500" />
          </div>
        )}
        <input
          className={`w-full ${Icon ? 'pl-12' : 'px-4'} pr-4 py-3.5 text-sm text-gray-900 bg-white border rounded-xl focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400 dark:bg-white/5 dark:border-white/10 dark:text-white dark:placeholder:text-gray-500 dark:focus:border-emerald-400 transition-all ${error ? 'border-error-500' : 'border-gray-200 dark:border-white/10'}`}
          {...props}
        />
      </div>
      {(error || helper) && (
        <p className={`mt-1.5 text-xs ${error ? 'text-error-500' : 'text-gray-500 dark:text-gray-400'}`}>
          {error || helper}
        </p>
      )}
    </div>
  );
}

// Simple Select Component (native HTML select)
export function SelectSimple({ label, error, helper, options = [], className = '', ...props }) {
  return (
    <div className={className}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
          {label}
        </label>
      )}
      <select
        className={`w-full px-4 py-2.5 text-sm text-gray-900 bg-white border rounded-lg focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 dark:bg-gray-900 dark:border-gray-700 dark:text-white cursor-pointer ${error ? 'border-error-500' : 'border-gray-300'}`}
        {...props}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
      {(error || helper) && (
        <p className={`mt-1.5 text-xs ${error ? 'text-error-500' : 'text-gray-500 dark:text-gray-400'}`}>
          {error || helper}
        </p>
      )}
    </div>
  );
}

// Alert Component
export function Alert({ variant = 'info', title, children, icon: Icon, onClose }) {
  const variants = {
    info: 'bg-brand-50 text-brand-800 dark:bg-brand-500/10 dark:text-brand-300 border-brand-200 dark:border-brand-800',
    success: 'bg-success-50 text-success-800 dark:bg-success-500/10 dark:text-success-300 border-success-200 dark:border-success-800',
    warning: 'bg-warning-50 text-warning-800 dark:bg-warning-500/10 dark:text-warning-300 border-warning-200 dark:border-warning-800',
    error: 'bg-error-50 text-error-800 dark:bg-error-500/10 dark:text-error-300 border-error-200 dark:border-error-800',
  };

  return (
    <div className={`p-4 rounded-lg border ${variants[variant]} flex items-start gap-3`}>
      {Icon && <Icon size={20} className="flex-shrink-0 mt-0.5" />}
      <div className="flex-1">
        {title && <p className="font-medium mb-1">{title}</p>}
        <div className="text-sm opacity-90">{children}</div>
      </div>
      {onClose && (
        <button onClick={onClose} className="flex-shrink-0 hover:opacity-70">
          <span className="sr-only">Fechar</span>
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </button>
      )}
    </div>
  );
}

// Progress Bar
export function Progress({ value = 0, max = 100, variant = 'primary', size = 'md', showLabel = false }) {
  const percent = Math.min(100, Math.max(0, (value / max) * 100));

  const variants = {
    primary: 'bg-brand-500',
    success: 'bg-success-500',
    warning: 'bg-warning-500',
    error: 'bg-error-500',
  };

  const sizes = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3',
  };

  return (
    <div className="flex items-center gap-3">
      <div className={`flex-1 bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden ${sizes[size]}`}>
        <div
          className={`h-full rounded-full transition-all duration-300 ${variants[variant]}`}
          style={{ width: `${percent}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300 min-w-[3rem] text-right">
          {Math.round(percent)}%
        </span>
      )}
    </div>
  );
}

// Empty State
export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      {Icon && (
        <div className="w-16 h-16 text-gray-300 dark:text-gray-600 mb-4">
          <Icon size={64} />
        </div>
      )}
      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">{title}</h3>
      {description && (
        <p className="text-sm text-gray-500 dark:text-gray-400 max-w-sm mb-4">{description}</p>
      )}
      {action}
    </div>
  );
}

// Loading Spinner
export function Spinner({ size = 'md', className = '' }) {
  const sizes = {
    sm: 'w-4 h-4 border-2',
    md: 'w-8 h-8 border-4',
    lg: 'w-12 h-12 border-4',
  };

  return (
    <div className={`${sizes[size]} border-gray-200 border-t-brand-500 rounded-full animate-spin ${className}`} />
  );
}

// Grid Layouts
export function StatsGrid({ children, columns = 4 }) {
  const colsClass = {
    2: 'sm:grid-cols-2',
    3: 'sm:grid-cols-2 lg:grid-cols-3',
    4: 'sm:grid-cols-2 lg:grid-cols-4',
  };

  return (
    <div className={`grid grid-cols-1 ${colsClass[columns]} gap-6`}>
      {children}
    </div>
  );
}

export function CardsGrid({ children, cols = 3 }) {
  const colsClass = {
    2: 'md:grid-cols-2',
    3: 'md:grid-cols-2 xl:grid-cols-3',
    4: 'md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4',
  };

  return (
    <div className={`grid grid-cols-1 ${colsClass[cols]} gap-6`}>
      {children}
    </div>
  );
}

// Checkbox Component
export function Checkbox({ label, checked, onChange, disabled = false, className = '', ...props }) {
  return (
    <label className={`flex items-center gap-2 cursor-pointer ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`}>
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        disabled={disabled}
        className="w-4 h-4 text-brand-500 bg-white border-gray-300 rounded focus:ring-brand-500 focus:ring-2 dark:bg-gray-900 dark:border-gray-700 cursor-pointer disabled:cursor-not-allowed"
        {...props}
      />
      {label && <span className="text-sm text-gray-700 dark:text-gray-300">{label}</span>}
    </label>
  );
}

// Label Component
export function Label({ children, htmlFor, required = false, className = '' }) {
  return (
    <label
      htmlFor={htmlFor}
      className={`block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5 ${className}`}
    >
      {children}
      {required && <span className="text-error-500 ml-1">*</span>}
    </label>
  );
}

// Switch Component
export function Switch({ checked, onChange, onCheckedChange, disabled = false, label, className = '' }) {
  const handleChange = (e) => {
    if (onChange) {
      onChange(e);
    }
    if (onCheckedChange) {
      onCheckedChange(e.target.checked);
    }
  };

  return (
    <label className={`flex items-center gap-3 cursor-pointer ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`}>
      <div className="relative">
        <input
          type="checkbox"
          checked={checked}
          onChange={handleChange}
          disabled={disabled}
          className="sr-only peer"
        />
        <div className={`w-11 h-6 rounded-full transition-colors ${checked ? 'bg-brand-500' : 'bg-gray-300 dark:bg-gray-700'} ${disabled ? 'cursor-not-allowed' : 'cursor-pointer'}`}></div>
        <div className={`absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform ${checked ? 'translate-x-5' : 'translate-x-0'}`}></div>
      </div>
      {label && <span className="text-sm text-gray-700 dark:text-gray-300">{label}</span>}
    </label>
  );
}

// Tabs Components
const TabsContext = React.createContext({ value: '', onValueChange: () => {} });

export function Tabs({ children, value, onValueChange, className = '' }) {
  return (
    <TabsContext.Provider value={{ value, onValueChange }}>
      <div className={className}>
        {children}
      </div>
    </TabsContext.Provider>
  );
}

export function TabsList({ children, className = '' }) {
  return (
    <div className={`inline-flex items-center gap-1 p-1 bg-gray-100 dark:bg-gray-800 rounded-lg ${className}`}>
      {children}
    </div>
  );
}

export function TabsTrigger({ children, value, className = '' }) {
  const { value: activeValue, onValueChange } = React.useContext(TabsContext);
  const isActive = activeValue === value;

  return (
    <button
      onClick={() => onValueChange(value)}
      className={`px-4 py-2 text-sm font-semibold rounded-md transition-all flex items-center ${
        isActive
          ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-md'
          : 'text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800/50'
      } ${className}`}
      data-state={isActive ? 'active' : 'inactive'}
    >
      {children}
    </button>
  );
}

export function TabsContent({ children, value, activeValue, className = '' }) {
  if (value !== activeValue) return null;
  return <div className={className}>{children}</div>;
}

// Slider Component
export function Slider({ value = [0], onValueChange, min = 0, max = 100, step = 1, className = '' }) {
  const handleChange = (e) => {
    const newValue = parseInt(e.target.value);
    onValueChange?.([newValue]);
  };

  return (
    <input
      type="range"
      min={min}
      max={max}
      step={step}
      value={value[0] || 0}
      onChange={handleChange}
      className={`w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-brand-500 ${className}`}
    />
  );
}

// Dropdown Menu Components
export function DropdownMenu({ children, open, onOpenChange }) {
  return (
    <div className="relative inline-block" data-open={open} data-onOpenChange={onOpenChange}>
      {children}
    </div>
  );
}

export function DropdownMenuTrigger({ children, asChild, ...props }) {
  if (asChild) {
    return <>{children}</>;
  }
  return <button {...props}>{children}</button>;
}

export function DropdownMenuContent({ children, align = 'end', className = '' }) {
  const alignClass = align === 'end' ? 'right-0' : 'left-0';
  return (
    <div className={`absolute ${alignClass} mt-2 w-56 rounded-lg bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-lg z-50 py-1 ${className}`}>
      {children}
    </div>
  );
}

export function DropdownMenuItem({ children, onClick, className = '' }) {
  return (
    <button
      onClick={onClick}
      className={`w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors flex items-center gap-2 ${className}`}
    >
      {children}
    </button>
  );
}

export function DropdownMenuSeparator() {
  return <div className="my-1 h-px bg-gray-200 dark:bg-gray-800" />;
}

export function DropdownMenuLabel({ children, className = '' }) {
  return (
    <div className={`px-4 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider ${className}`}>
      {children}
    </div>
  );
}

// Alert Dialog Components
export function AlertDialog({ children, open, onOpenChange }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" onClick={() => onOpenChange?.(false)} />
      <div className="relative z-50" data-open={open} data-onOpenChange={onOpenChange}>
        {children}
      </div>
    </div>
  );
}

export function AlertDialogTrigger({ children, asChild, ...props }) {
  if (asChild) {
    return <>{children}</>;
  }
  return <button {...props}>{children}</button>;
}

export function AlertDialogContent({ children, className = '' }) {
  return (
    <div className={`bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-xl max-w-md w-full mx-4 ${className}`}>
      {children}
    </div>
  );
}

export function AlertDialogHeader({ children, className = '' }) {
  return <div className={`p-6 pb-4 ${className}`}>{children}</div>;
}

export function AlertDialogTitle({ children, className = '' }) {
  return <h2 className={`text-lg font-semibold text-gray-900 dark:text-white ${className}`}>{children}</h2>;
}

export function AlertDialogDescription({ children, className = '' }) {
  return <p className={`text-sm text-gray-500 dark:text-gray-400 mt-2 ${className}`}>{children}</p>;
}

export function AlertDialogFooter({ children, className = '' }) {
  return <div className={`p-6 pt-4 flex items-center gap-3 justify-end ${className}`}>{children}</div>;
}

export function AlertDialogAction({ children, onClick, className = '' }) {
  return (
    <Button variant="primary" onClick={onClick} className={className}>
      {children}
    </Button>
  );
}

export function AlertDialogCancel({ children, onClick, className = '' }) {
  return (
    <Button variant="outline" onClick={onClick} className={className}>
      {children}
    </Button>
  );
}

// Popover Components
export function Popover({ children, open, onOpenChange }) {
  return (
    <div className="relative inline-block" data-open={open} data-onOpenChange={onOpenChange}>
      {children}
    </div>
  );
}

export function PopoverTrigger({ children, asChild, ...props }) {
  if (asChild) {
    return <>{children}</>;
  }
  return <button {...props}>{children}</button>;
}

export function PopoverContent({ children, align = 'center', className = '' }) {
  const alignClass = align === 'end' ? 'right-0' : align === 'start' ? 'left-0' : 'left-1/2 -translate-x-1/2';
  return (
    <div className={`absolute ${alignClass} mt-2 w-80 rounded-lg bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-lg z-50 p-4 ${className}`}>
      {children}
    </div>
  );
}

// Avatar Components
export function Avatar({ children, className = '' }) {
  return (
    <div className={`relative inline-flex items-center justify-center rounded-full overflow-hidden ${className}`}>
      {children}
    </div>
  );
}

export function AvatarImage({ src, alt, className = '' }) {
  return <img src={src} alt={alt} className={`w-full h-full object-cover ${className}`} />;
}

export function AvatarFallback({ children, className = '' }) {
  return (
    <div className={`flex items-center justify-center w-full h-full bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-sm font-medium ${className}`}>
      {children}
    </div>
  );
}

// Compound Select Components with state management
const SelectContext = React.createContext({});

export function SelectCompound({ value, onValueChange, children, className = '' }) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedLabel, setSelectedLabel] = useState('');
  const selectRef = useRef(null);
  const optionsMapRef = useRef({});

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (selectRef.current && !selectRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Register options for label lookup - using ref to avoid re-renders
  const registerOption = useCallback((optValue, optLabel) => {
    if (optionsMapRef.current[optValue] !== optLabel) {
      optionsMapRef.current[optValue] = optLabel;
    }
  }, []);

  // Get display label for current value
  const getDisplayLabel = useCallback(() => {
    if (selectedLabel) return selectedLabel;
    if (optionsMapRef.current[value]) return optionsMapRef.current[value];
    return value || '';
  }, [selectedLabel, value]);

  const handleValueChange = useCallback((val, label) => {
    onValueChange?.(val);
    setSelectedLabel(typeof label === 'string' ? label : String(label));
    setIsOpen(false);
  }, [onValueChange]);

  const contextValue = {
    value,
    isOpen,
    setIsOpen,
    onValueChange: handleValueChange,
    selectedLabel,
    setSelectedLabel,
    registerOption,
    getDisplayLabel
  };

  return (
    <SelectContext.Provider value={contextValue}>
      <div ref={selectRef} className={`relative ${className}`}>
        {children}
      </div>
    </SelectContext.Provider>
  );
}

export function SelectTrigger({ children, className = '', ...props }) {
  const { isOpen, setIsOpen } = React.useContext(SelectContext);
  return (
    <button
      type="button"
      onClick={() => setIsOpen(!isOpen)}
      className={`w-full px-4 py-3.5 text-sm text-left text-gray-900 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400 dark:bg-white/5 dark:border-white/10 dark:text-white flex items-center justify-between transition-all ${className}`}
      {...props}
    >
      {children}
      <svg className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    </button>
  );
}

export function SelectValue({ placeholder }) {
  const { getDisplayLabel } = React.useContext(SelectContext);
  const displayLabel = getDisplayLabel ? getDisplayLabel() : '';
  return <span className="truncate">{displayLabel || placeholder}</span>;
}

export function SelectContent({ children, className = '' }) {
  const { isOpen } = React.useContext(SelectContext);

  // Always render children for option registration, but hide when closed
  return (
    <div
      className={`absolute mt-2 w-full rounded-xl bg-white dark:bg-[#1a1a1a] border border-gray-200 dark:border-white/10 shadow-2xl z-50 max-h-60 overflow-auto py-2 ${className}`}
      style={{
        visibility: isOpen ? 'visible' : 'hidden',
        opacity: isOpen ? 1 : 0,
        pointerEvents: isOpen ? 'auto' : 'none'
      }}
    >
      {children}
    </div>
  );
}

export function SelectItem({ children, value, className = '' }) {
  const { value: selectedValue, onValueChange, registerOption } = React.useContext(SelectContext);
  const isSelected = selectedValue === value;
  const registeredRef = useRef(false);

  // Register this option's value and label on mount only
  useEffect(() => {
    if (registerOption && !registeredRef.current) {
      const label = typeof children === 'string' ? children : String(children);
      registerOption(value, label);
      registeredRef.current = true;
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <button
      type="button"
      onClick={() => onValueChange(value, children)}
      className={`w-full px-4 py-3 text-left text-sm transition-all flex items-center justify-between mx-2 rounded-lg ${
        isSelected
          ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-medium'
          : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-white/5'
      } ${className}`}
      style={{ width: 'calc(100% - 16px)' }}
    >
      <span>{children}</span>
      {isSelected && (
        <svg className="w-4 h-4 text-emerald-500" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
      )}
    </button>
  );
}

// Main Select export (use the compound version)
export { SelectCompound as Select };
