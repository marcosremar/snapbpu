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
  Cloud,
  Server,
  DollarSign,
  Shield
} from "lucide-react";
import DumontLogo from "../DumontLogo";

// Helper to get base path based on demo mode
function useBasePath() {
  const location = useLocation();
  return location.pathname.startsWith('/demo-app') ? '/demo-app' : '/app';
}

const AppHeader = ({ user, onLogout, isDemo = false, dashboardStats = null }) => {
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
    <header className="sticky top-0 flex w-full bg-white border-b border-gray-200 z-[99999] dark:border-white/5 dark:bg-[#0a0d0a]">
      <div className="flex items-center justify-between w-full px-4 py-3 lg:px-6">
        {/* Left side */}
        <div className="flex items-center gap-4">
          {/* Sidebar Toggle */}
          <button
            className="flex items-center justify-center w-10 h-10 text-gray-500 rounded-lg hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-[#1a1f1a]"
            onClick={handleToggle}
            aria-label="Toggle Sidebar"
          >
            {isMobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>

          {/* Mobile Logo */}
          <Link to={basePath} className="flex items-center gap-2 lg:hidden">
            <DumontLogo size={32} />
            <span className="text-lg font-bold text-gray-900 dark:text-white">Dumont Cloud</span>
          </Link>
        </div>

        {/* Right side */}
        <div className="flex items-center gap-3">
          {/* Dashboard Stats - Only show on dashboard page */}
          {dashboardStats && (
            <>
              <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/5 border border-white/10">
                <Server className="w-4 h-4 text-brand-400" />
                <div>
                  <p className="text-[10px] text-gray-400 leading-none">Máquinas</p>
                  <p className="text-xs font-bold text-white leading-none mt-0.5">{dashboardStats.activeMachines}/{dashboardStats.totalMachines}</p>
                </div>
              </div>

              <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/5 border border-white/10">
                <DollarSign className="w-4 h-4 text-yellow-400" />
                <div>
                  <p className="text-[10px] text-gray-400 leading-none">Custo/Dia</p>
                  <p className="text-xs font-bold text-white leading-none mt-0.5">${dashboardStats.dailyCost}</p>
                </div>
              </div>

              <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/5 border border-white/10">
                <Shield className="w-4 h-4 text-brand-400" />
                <div>
                  <p className="text-[10px] text-gray-400 leading-none">Economia</p>
                  <p className="text-xs font-bold text-brand-500 leading-none mt-0.5">${dashboardStats.savings} <span className="text-[9px] text-brand-400">+89%</span></p>
                </div>
              </div>

              <div className="h-8 w-px bg-white/10 hidden lg:block" />
            </>
          )}
          {/* TODO: Dark Mode Toggle - será implementado no futuro
          <button
            onClick={toggleTheme}
            className="flex items-center justify-center w-10 h-10 text-gray-500 rounded-lg hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-[#1a1f1a]"
            aria-label="Toggle Dark Mode"
          >
            {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
          </button>
          */}

          {/* Notifications */}
          <div className="relative" ref={notificationRef}>
            <button
              onClick={() => setNotificationOpen(!isNotificationOpen)}
              className="relative flex items-center justify-center w-10 h-10 text-gray-500 rounded-lg hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-[#1a1f1a]"
              aria-label="Notifications"
            >
              <Bell size={20} />
              <span className="absolute top-2 right-2 w-2 h-2 bg-error-500 rounded-full"></span>
            </button>

            {/* Notification Dropdown */}
            {isNotificationOpen && (
              <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-theme-lg border border-gray-200 dark:bg-[#131713] dark:border-gray-800">
                <div className="p-4 border-b border-gray-200 dark:border-gray-800">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Notificações</h3>
                </div>
                <div className="max-h-80 overflow-y-auto">
                  <div className="p-4 hover:bg-gray-50 dark:hover:bg-[#1a1f1a] border-b border-gray-100 dark:border-gray-800">
                    <p className="text-sm text-gray-800 dark:text-gray-200">Sua máquina GPU entrou em standby</p>
                    <p className="text-xs text-gray-500 mt-1">Há 2 minutos</p>
                  </div>
                  <div className="p-4 hover:bg-gray-50 dark:hover:bg-[#1a1f1a]">
                    <p className="text-sm text-gray-800 dark:text-gray-200">Economia de $12.50 hoje</p>
                    <p className="text-xs text-gray-500 mt-1">Há 1 hora</p>
                  </div>
                </div>
                <div className="p-3 border-t border-gray-200 dark:border-gray-800">
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
              className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-[#1a1f1a]"
            >
              <div className="w-8 h-8 bg-brand-500 rounded-lg flex items-center justify-center shadow-lg shadow-brand-500/20">
                <User size={18} className="text-white" />
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
              <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-theme-lg border border-gray-200 dark:bg-[#131713] dark:border-gray-800">
                <div className="p-4 border-b border-gray-200 dark:border-gray-800">
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
                    className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 rounded-lg hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-[#1a1f1a]"
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
