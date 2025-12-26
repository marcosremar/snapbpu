import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Server,
  Zap,
  BarChart3,
  Settings,
  ChevronDown,
  MoreHorizontal,
  Cloud,
  Brain,
  BookOpen,
  Sparkles,
  Play,
  Columns,
  Rocket,
  Wallet,
  RefreshCw
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_URL || '';
import { useSidebar } from "../../context/SidebarContext";
import Logo, { LogoIcon } from "../Logo";

// Helper to get base path based on demo mode
function useBasePath() {
  const location = useLocation();
  return location.pathname.startsWith('/demo-app') ? '/demo-app' : '/app';
}

const AppSidebar = ({ isDemo = false }) => {
  const { isExpanded, isMobileOpen, isHovered, setIsHovered } = useSidebar();
  const location = useLocation();
  const basePath = useBasePath();

  const [openSubmenu, setOpenSubmenu] = useState(null);
  const [subMenuHeight, setSubMenuHeight] = useState({});
  const subMenuRefs = useRef({});

  // Balance state
  const [balance, setBalance] = useState(null);
  const [loadingBalance, setLoadingBalance] = useState(false);

  // Fetch balance
  const fetchBalance = useCallback(async () => {
    if (isDemo) {
      setBalance({ credit: 4.94, balance: 4.94 });
      return;
    }

    const token = localStorage.getItem('token');
    if (!token) return;

    setLoadingBalance(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/balance`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setBalance(data);
      }
    } catch (e) {
      console.error('Failed to fetch balance:', e);
    }
    setLoadingBalance(false);
  }, [isDemo]);

  useEffect(() => {
    fetchBalance();
    // Refresh balance every 60 seconds
    const interval = setInterval(fetchBalance, 60000);
    return () => clearInterval(interval);
  }, [fetchBalance]);

  const navItems = [
    {
      icon: LayoutDashboard,
      name: "Dashboard",
      path: basePath,
    },
    {
      icon: Server,
      name: "Machines",
      path: `${basePath}/machines`,
    },
    {
      icon: Zap,
      name: "Serverless",
      path: `${basePath}/serverless`,
    },
    {
      icon: Play,
      name: "Jobs",
      path: `${basePath}/jobs`,
    },
    {
      icon: Rocket,
      name: "Models",
      path: `${basePath}/models`,
    },
    {
      icon: Brain,
      name: "Fine-Tuning",
      path: `${basePath}/finetune`,
    },
    {
      icon: Columns,
      name: "Chat Arena",
      path: `${basePath}/chat-arena`,
    },
    {
      name: "Analytics",
      icon: BarChart3,
      path: `${basePath}/metrics-hub`,
    },
    {
      icon: Settings,
      name: "Settings",
      path: `${basePath}/settings`,
    },
    // Documentação temporariamente desabilitada no demo
    ...(!isDemo ? [{
      icon: BookOpen,
      name: "Documentação",
      path: "/docs",
    }] : []),
  ];

  const isActive = useCallback(
    (path) => {
      if (path === basePath) {
        return location.pathname === path;
      }
      return location.pathname === path || location.pathname.startsWith(`${path}/`);
    },
    [location.pathname, basePath]
  );

  useEffect(() => {
    let submenuMatched = false;
    navItems.forEach((nav, index) => {
      if (nav.subItems) {
        nav.subItems.forEach((subItem) => {
          if (isActive(subItem.path)) {
            setOpenSubmenu(index);
            submenuMatched = true;
          }
        });
      }
    });

    if (!submenuMatched) {
      setOpenSubmenu(null);
    }
  }, [location.pathname]);

  useEffect(() => {
    if (openSubmenu !== null) {
      const key = `submenu-${openSubmenu}`;
      if (subMenuRefs.current[key]) {
        setSubMenuHeight((prevHeights) => ({
          ...prevHeights,
          [key]: subMenuRefs.current[key]?.scrollHeight || 0,
        }));
      }
    }
  }, [openSubmenu]);

  const handleSubmenuToggle = (index) => {
    setOpenSubmenu((prevOpenSubmenu) => {
      if (prevOpenSubmenu === index) {
        return null;
      }
      return index;
    });
  };

  const renderMenuItems = (items) => (
    <ul className="flex flex-col gap-2">
      {items.map((nav, index) => {
        const Icon = nav.icon;
        const isItemActive = nav.path ? isActive(nav.path) : nav.subItems?.some(sub => isActive(sub.path));

        return (
          <li key={nav.name}>
            {nav.subItems ? (
              <button
                onClick={() => handleSubmenuToggle(index)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-semibold transition-colors cursor-pointer ${isItemActive
                  ? "bg-brand-800/10 text-brand-800 dark:text-brand-500"
                  : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-white/5 hover:text-gray-900 dark:hover:text-gray-100"
                  } ${!isExpanded && !isHovered
                    ? "lg:justify-center"
                    : "lg:justify-start"
                  }`}
              >
                <Icon
                  size={20}
                  className={isItemActive ? "text-brand-800 dark:text-brand-500" : "text-gray-600 dark:text-gray-300"}
                />
                {(isExpanded || isHovered || isMobileOpen) && (
                  <span>{nav.name}</span>
                )}
                {(isExpanded || isHovered || isMobileOpen) && (
                  <ChevronDown
                    size={16}
                    className={`ml-auto transition-transform duration-200 ${openSubmenu === index
                      ? "rotate-180 text-brand-500"
                      : "text-gray-400"
                      }`}
                  />
                )}
              </button>
            ) : (
              <Link
                to={nav.path}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-semibold transition-colors ${isActive(nav.path)
                  ? "bg-brand-800/10 text-brand-800 dark:text-brand-500"
                  : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-white/5 hover:text-gray-900 dark:hover:text-gray-100"
                  } ${!isExpanded && !isHovered
                    ? "lg:justify-center"
                    : "lg:justify-start"
                  }`}
              >
                <Icon
                  size={20}
                  className={isActive(nav.path) ? "text-brand-800 dark:text-brand-500" : "text-gray-600 dark:text-gray-300"}
                />
                {(isExpanded || isHovered || isMobileOpen) && (
                  <span>{nav.name}</span>
                )}
              </Link>
            )}
            {nav.subItems && (isExpanded || isHovered || isMobileOpen) && (
              <div
                ref={(el) => {
                  subMenuRefs.current[`submenu-${index}`] = el;
                }}
                className="overflow-hidden transition-all duration-300"
                style={{
                  height:
                    openSubmenu === index
                      ? `${subMenuHeight[`submenu-${index}`]}px`
                      : "0px",
                }}
              >
                <ul className="mt-2 space-y-1 ml-9">
                  {nav.subItems.map((subItem) => {
                    const SubIcon = subItem.icon;
                    return (
                      <li key={subItem.name}>
                        <Link
                          to={subItem.path}
                          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${isActive(subItem.path)
                            ? "bg-brand-400/10 text-brand-400"
                            : "text-gray-400 hover:bg-white/5 hover:text-gray-200"
                            }`}
                        >
                          {SubIcon && <SubIcon size={16} />}
                          {subItem.name}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );

  return (
    <aside
      className={`fixed mt-16 flex flex-col lg:mt-0 top-0 px-4 left-0 bg-white dark:bg-[#0a0d0a] dark:border-white/5 text-gray-900 h-screen transition-all duration-300 ease-in-out z-50 border-r border-gray-200
        ${isExpanded || isMobileOpen
          ? "w-[260px]"
          : isHovered
            ? "w-[260px]"
            : "w-[80px]"
        }
        ${isMobileOpen ? "translate-x-0" : "-translate-x-full"}
        lg:translate-x-0`}
      onMouseEnter={() => !isExpanded && setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Logo */}
      <div
        className={`py-6 flex ${!isExpanded && !isHovered ? "lg:justify-center" : "justify-start"
          }`}
      >
        <Link to={basePath} className="flex items-center gap-2">
          {(isExpanded || isHovered || isMobileOpen) ? (
            <div className="flex items-center gap-1">
              <Logo />
              {isDemo && (
                <span className="ml-2 px-2 py-0.5 text-xs font-bold bg-amber-500 text-black rounded border-b-2 border-amber-600">
                  DEMO
                </span>
              )}
            </div>
          ) : (
            <LogoIcon />
          )}
        </Link>
      </div>

      {/* Navigation */}
      <div className="flex flex-col overflow-y-auto duration-300 ease-linear flex-1 no-scrollbar">
        <nav className="mb-6">
          <div className="flex flex-col gap-4">
            <div>
              <h2
                className={`mb-3 text-xs uppercase tracking-wider flex text-gray-400 font-medium ${!isExpanded && !isHovered
                  ? "lg:justify-center"
                  : "justify-start px-3"
                  }`}
              >
                {isExpanded || isHovered || isMobileOpen ? (
                  "Menu"
                ) : (
                  <MoreHorizontal size={20} />
                )}
              </h2>
              {renderMenuItems(navItems)}
            </div>
          </div>
        </nav>

        {/* Balance Widget */}
        {(isExpanded || isHovered || isMobileOpen) && balance && (
          <div className="mt-auto px-2 mb-3">
            <div className="relative p-3 rounded-xl bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 border border-green-200 dark:border-green-800/30 overflow-hidden">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-md bg-green-500/20 flex items-center justify-center">
                    <Wallet className="w-3.5 h-3.5 text-green-600 dark:text-green-400" />
                  </div>
                  <span className="text-gray-600 dark:text-gray-400 font-medium text-xs">Saldo VAST.ai</span>
                </div>
                <button
                  onClick={fetchBalance}
                  disabled={loadingBalance}
                  className="p-1 rounded hover:bg-green-500/10 transition-colors"
                  title="Atualizar saldo"
                >
                  <RefreshCw className={`w-3 h-3 text-green-600 dark:text-green-400 ${loadingBalance ? 'animate-spin' : ''}`} />
                </button>
              </div>
              <div className="text-xl font-bold text-green-700 dark:text-green-300">
                ${(balance.credit || balance.balance || 0).toFixed(2)}
              </div>
              {balance.balance < 1 && (
                <p className="text-amber-600 dark:text-amber-400 text-[10px] mt-1">
                  ⚠️ Saldo baixo - adicione créditos
                </p>
              )}
            </div>
          </div>
        )}

        {/* Promo Widget - Subtle */}
        {(isExpanded || isHovered || isMobileOpen) && (
          <div className="mb-10 px-2">
            <div className="relative p-3 rounded-xl bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 overflow-hidden">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-6 h-6 rounded-md bg-brand-800/10 dark:bg-brand-500/10 flex items-center justify-center">
                  <Cloud className="w-3.5 h-3.5 text-brand-800 dark:text-brand-500" />
                </div>
                <span className="text-gray-700 dark:text-gray-300 font-medium text-xs">GPU Cloud</span>
              </div>
              <p className="text-gray-500 dark:text-gray-500 text-[10px] leading-relaxed mb-2">
                GPUs de alto desempenho com até 80% de economia.
              </p>
              <Link
                to={isDemo ? "/demo-app/gpu-offers" : "/app/gpu-offers"}
                className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-transparent hover:bg-brand-800/10 dark:hover:bg-brand-500/10 border border-gray-200 dark:border-white/10 text-gray-600 dark:text-gray-400 hover:text-brand-800 dark:hover:text-brand-500 text-[10px] font-medium transition-all"
              >
                <Sparkles className="w-3 h-3" />
                Explorar Ofertas
              </Link>
            </div>
          </div>
        )}
      </div>


    </aside>
  );
};

export default AppSidebar;
