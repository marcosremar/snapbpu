import { useState, useRef, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { useSidebar } from "../../context/SidebarContext";
import { useTheme } from "../../context/ThemeContext";
import {
  Menu,
  X,
  Search,
  Bell,
  Moon,
  Sun,
  ChevronDown,
  User,
  LogOut,
  Cloud
} from "lucide-react";

// Helper to get base path based on demo mode
function useBasePath() {
  const location = useLocation();
  return location.pathname.startsWith('/demo-app') ? '/demo-app' : '/app';
}

const AppHeader = ({ user, onLogout, isDemo = false }) => {
  const [isNotificationOpen, setNotificationOpen] = useState(false);
  const [isUserMenuOpen, setUserMenuOpen] = useState(false);

  const { isMobileOpen, toggleSidebar, toggleMobileSidebar } = useSidebar();
  const { theme, toggleTheme } = useTheme();
  const basePath = useBasePath();

  const notificationRef = useRef(null);
  const userMenuRef = useRef(null);

  const handleToggle = () => {
    if (window.innerWidth >= 1024) {
      toggleSidebar();
    } else {
      toggleMobileSidebar();
    }
  };

  // Close dropdowns on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (notificationRef.current && !notificationRef.current.contains(event.target)) {
        setNotificationOpen(false);
      }
      if (userMenuRef.current && !userMenuRef.current.contains(event.target)) {
        setUserMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className="sticky top-0 flex w-full bg-white border-b border-gray-200 z-[99999] dark:border-dark-surface-border dark:bg-dark-surface-card">
      <div className="flex items-center justify-between w-full px-4 py-3 lg:px-6">
        {/* Left side */}
        <div className="flex items-center gap-4">
          {/* Sidebar Toggle */}
          <button
            className="flex items-center justify-center w-10 h-10 text-gray-500 rounded-lg hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-dark-surface-hover"
            onClick={handleToggle}
            aria-label="Toggle Sidebar"
          >
            {isMobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>

          {/* Mobile Logo */}
          <Link to={basePath} className="flex items-center gap-2 lg:hidden">
            <div className="w-8 h-8 bg-gradient-to-br from-brand-500 to-brand-600 rounded-lg flex items-center justify-center">
              <Cloud size={20} className="text-white" />
            </div>
            <span className="text-lg font-semibold text-gray-900 dark:text-white">Dumont</span>
            <span className="text-lg font-semibold text-brand-500">Cloud</span>
          </Link>

          {/* Search Bar - Desktop */}
          <div className="hidden lg:block">
            <div className="relative">
              <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Buscar..."
                className="w-[300px] h-10 pl-10 pr-4 text-sm text-gray-800 bg-gray-50 border border-gray-200 rounded-lg focus:border-brand-300 focus:ring-2 focus:ring-brand-500/10 focus:outline-none dark:bg-dark-surface-secondary dark:border-dark-surface-border dark:text-gray-200 dark:placeholder:text-gray-500"
              />
            </div>
          </div>
        </div>

        {/* Right side */}
        <div className="flex items-center gap-2">
          {/* Dark Mode Toggle */}
          <button
            onClick={toggleTheme}
            className="flex items-center justify-center w-10 h-10 text-gray-500 rounded-lg hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-dark-surface-hover"
            aria-label="Toggle Dark Mode"
          >
            {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
          </button>

          {/* Notifications */}
          <div className="relative" ref={notificationRef}>
            <button
              onClick={() => setNotificationOpen(!isNotificationOpen)}
              className="relative flex items-center justify-center w-10 h-10 text-gray-500 rounded-lg hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-dark-surface-hover"
              aria-label="Notifications"
            >
              <Bell size={20} />
              <span className="absolute top-2 right-2 w-2 h-2 bg-error-500 rounded-full"></span>
            </button>

            {/* Notification Dropdown */}
            {isNotificationOpen && (
              <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-theme-lg border border-gray-200 dark:bg-dark-surface-card dark:border-dark-surface-border">
                <div className="p-4 border-b border-gray-200 dark:border-dark-surface-border">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Notificações</h3>
                </div>
                <div className="max-h-80 overflow-y-auto">
                  <div className="p-4 hover:bg-gray-50 dark:hover:bg-dark-surface-hover border-b border-gray-100 dark:border-dark-surface-border">
                    <p className="text-sm text-gray-800 dark:text-gray-200">Sua máquina GPU entrou em standby</p>
                    <p className="text-xs text-gray-500 mt-1">Há 2 minutos</p>
                  </div>
                  <div className="p-4 hover:bg-gray-50 dark:hover:bg-dark-surface-hover">
                    <p className="text-sm text-gray-800 dark:text-gray-200">Economia de $12.50 hoje</p>
                    <p className="text-xs text-gray-500 mt-1">Há 1 hora</p>
                  </div>
                </div>
                <div className="p-3 border-t border-gray-200 dark:border-dark-surface-border">
                  <Link
                    to={`${basePath}/settings`}
                    className="text-sm text-brand-500 hover:text-brand-600 font-medium"
                    onClick={() => setNotificationOpen(false)}
                  >
                    Ver todas
                  </Link>
                </div>
              </div>
            )}
          </div>

          {/* User Menu */}
          <div className="relative" ref={userMenuRef}>
            <button
              onClick={() => setUserMenuOpen(!isUserMenuOpen)}
              className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-surface-hover"
            >
              <div className="w-8 h-8 bg-brand-100 rounded-full flex items-center justify-center">
                <User size={18} className="text-brand-600" />
              </div>
              <div className="hidden md:block text-left">
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {user?.username?.split('@')[0] || 'Usuário'}
                </p>
                <p className="text-xs text-gray-500">
                  {isDemo ? 'Demo Mode' : 'Admin'}
                </p>
              </div>
              <ChevronDown size={16} className="text-gray-400 hidden md:block" />
            </button>

            {/* User Dropdown */}
            {isUserMenuOpen && (
              <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-theme-lg border border-gray-200 dark:bg-dark-surface-card dark:border-dark-surface-border">
                <div className="p-4 border-b border-gray-200 dark:border-dark-surface-border">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {user?.username || 'Usuário'}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {isDemo ? 'Conta Demo' : 'Conta Pro'}
                  </p>
                </div>
                <div className="p-2">
                  <Link
                    to={`${basePath}/settings`}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 rounded-lg hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-dark-surface-hover"
                    onClick={() => setUserMenuOpen(false)}
                  >
                    <User size={16} />
                    Meu Perfil
                  </Link>
                  <button
                    onClick={() => {
                      setUserMenuOpen(false);
                      onLogout();
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-error-600 rounded-lg hover:bg-error-50 dark:text-error-400 dark:hover:bg-error-500/10"
                  >
                    <LogOut size={16} />
                    {isDemo ? 'Sair do Demo' : 'Logout'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

export default AppHeader;
