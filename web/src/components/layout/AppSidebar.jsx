import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Server,
  BarChart3,
  PiggyBank,
  Bot,
  Settings,
  ChevronDown,
  MoreHorizontal,
  Cloud,
  Brain,
  BookOpen
} from "lucide-react";
import { useSidebar } from "../../context/SidebarContext";

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
      icon: Brain,
      name: "Fine-Tuning",
      path: `${basePath}/finetune`,
    },
    {
      name: "Analytics",
      icon: BarChart3,
      subItems: [
        { name: "Métricas", path: `${basePath}/metrics-hub`, icon: BarChart3 },
        { name: "Economia", path: `${basePath}/savings`, icon: PiggyBank },
        { name: "AI Advisor", path: `${basePath}/advisor`, icon: Bot },
      ],
    },
    {
      icon: Settings,
      name: "Settings",
      path: `${basePath}/settings`,
    },
    {
      icon: BookOpen,
      name: "Documentação",
      path: isDemo ? "/demo-docs" : "/docs",
    },
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
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
                  isItemActive
                    ? "bg-brand-50 text-brand-500 dark:bg-brand-500/10 dark:text-brand-400"
                    : "text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-dark-surface-hover"
                } ${
                  !isExpanded && !isHovered
                    ? "lg:justify-center"
                    : "lg:justify-start"
                }`}
              >
                <Icon
                  size={20}
                  className={isItemActive ? "text-brand-500 dark:text-brand-400" : "text-gray-500 dark:text-gray-400"}
                />
                {(isExpanded || isHovered || isMobileOpen) && (
                  <span>{nav.name}</span>
                )}
                {(isExpanded || isHovered || isMobileOpen) && (
                  <ChevronDown
                    size={16}
                    className={`ml-auto transition-transform duration-200 ${
                      openSubmenu === index
                        ? "rotate-180 text-brand-500"
                        : "text-gray-400"
                    }`}
                  />
                )}
              </button>
            ) : (
              <Link
                to={nav.path}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive(nav.path)
                    ? "bg-brand-50 text-brand-500 dark:bg-brand-500/10 dark:text-brand-400"
                    : "text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-dark-surface-hover"
                } ${
                  !isExpanded && !isHovered
                    ? "lg:justify-center"
                    : "lg:justify-start"
                }`}
              >
                <Icon
                  size={20}
                  className={isActive(nav.path) ? "text-brand-500 dark:text-brand-400" : "text-gray-500 dark:text-gray-400"}
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
                          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${
                            isActive(subItem.path)
                              ? "bg-brand-50 text-brand-500 dark:bg-brand-500/10 dark:text-brand-400"
                              : "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-dark-surface-hover"
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
      className={`fixed mt-16 flex flex-col lg:mt-0 top-0 px-4 left-0 bg-white dark:bg-dark-surface-card dark:border-dark-surface-border text-gray-900 h-screen transition-all duration-300 ease-in-out z-50 border-r border-gray-200
        ${
          isExpanded || isMobileOpen
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
        className={`py-6 flex ${
          !isExpanded && !isHovered ? "lg:justify-center" : "justify-start"
        }`}
      >
        <Link to={basePath} className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-brand-500 to-brand-600 rounded-lg flex items-center justify-center">
            <Cloud size={20} className="text-white" />
          </div>
          {(isExpanded || isHovered || isMobileOpen) && (
            <div className="flex items-center gap-1">
              <span className="text-lg font-semibold text-gray-900 dark:text-white">Dumont</span>
              <span className="text-lg font-semibold text-brand-500">Cloud</span>
              {isDemo && (
                <span className="ml-2 px-1.5 py-0.5 text-xs font-medium bg-warning-100 text-warning-700 rounded">
                  DEMO
                </span>
              )}
            </div>
          )}
        </Link>
      </div>

      {/* Navigation */}
      <div className="flex flex-col overflow-y-auto duration-300 ease-linear flex-1 no-scrollbar">
        <nav className="mb-6">
          <div className="flex flex-col gap-4">
            <div>
              <h2
                className={`mb-3 text-xs uppercase tracking-wider flex text-gray-400 font-medium ${
                  !isExpanded && !isHovered
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
      </div>

      {/* Sidebar Widget */}
      {(isExpanded || isHovered || isMobileOpen) && (
        <div className="p-4 mb-4 mx-1 bg-gradient-to-br from-brand-500 to-brand-600 rounded-xl">
          <h3 className="text-sm font-semibold text-white mb-1">GPU Cloud</h3>
          <p className="text-xs text-brand-100 mb-3">
            Economize até 80% com spot instances
          </p>
          <a
            href={`${basePath}/machines`}
            className="block w-full py-2 px-3 text-xs font-medium text-center text-brand-600 bg-white rounded-lg hover:bg-brand-50 transition-colors"
          >
            Ver Máquinas
          </a>
        </div>
      )}
    </aside>
  );
};

export default AppSidebar;
