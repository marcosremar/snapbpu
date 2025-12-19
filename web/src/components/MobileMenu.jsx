import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { Menu, X, Home, Server, Settings, BarChart3, LogOut, PiggyBank, Bot, ChevronDown } from 'lucide-react'

export default function MobileMenu({ onLogout, basePath = '/app' }) {
  const [isOpen, setIsOpen] = useState(false)
  const [analyticsOpen, setAnalyticsOpen] = useState(false)
  const isDemoMode = basePath === '/demo-app'

  const mainLinks = [
    { to: basePath, icon: Home, label: 'Dashboard', end: true },
    { to: `${basePath}/machines`, icon: Server, label: 'Machines' },
  ]

  const analyticsLinks = [
    { to: `${basePath}/metrics-hub`, icon: BarChart3, label: 'Métricas' },
    { to: `${basePath}/savings`, icon: PiggyBank, label: 'Economia' },
    { to: `${basePath}/advisor`, icon: Bot, label: 'AI Advisor' },
  ]

  const bottomLinks = [
    { to: `${basePath}/settings`, icon: Settings, label: 'Settings' },
  ]

  const closeMenu = () => setIsOpen(false)

  return (
    <>
      {/* Hamburger Button - visível apenas em mobile */}
      <button
        className="mobile-menu-button"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Menu"
      >
        {isOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      {/* Overlay escuro */}
      {isOpen && (
        <div
          className="mobile-menu-overlay"
          onClick={closeMenu}
        />
      )}

      {/* Menu Drawer */}
      <div className={`mobile-menu-drawer ${isOpen ? 'open' : ''}`}>
        <div className="mobile-menu-header">
          <span className="mobile-menu-title">Dumont <span className="text-green-400">Cloud</span></span>
        </div>

        <nav className="mobile-menu-nav">
          {/* Main links */}
          {mainLinks.map(link => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              onClick={closeMenu}
              className={({ isActive }) =>
                `mobile-menu-link ${isActive ? 'active' : ''}`
              }
            >
              <link.icon size={20} />
              {link.label}
            </NavLink>
          ))}

          {/* Analytics dropdown */}
          <div className="mobile-menu-section">
            <button
              className={`mobile-menu-link mobile-menu-dropdown-trigger ${analyticsOpen ? 'open' : ''}`}
              onClick={() => setAnalyticsOpen(!analyticsOpen)}
            >
              <BarChart3 size={20} />
              Analytics
              <ChevronDown size={16} className={`ml-auto transition-transform ${analyticsOpen ? 'rotate-180' : ''}`} />
            </button>
            {analyticsOpen && (
              <div className="mobile-menu-submenu">
                {analyticsLinks.map(link => (
                  <NavLink
                    key={link.to}
                    to={link.to}
                    onClick={closeMenu}
                    className={({ isActive }) =>
                      `mobile-menu-link mobile-menu-sublink ${isActive ? 'active' : ''}`
                    }
                  >
                    <link.icon size={18} />
                    {link.label}
                  </NavLink>
                ))}
              </div>
            )}
          </div>

          {/* Bottom links */}
          {bottomLinks.map(link => (
            <NavLink
              key={link.to}
              to={link.to}
              onClick={closeMenu}
              className={({ isActive }) =>
                `mobile-menu-link ${isActive ? 'active' : ''}`
              }
            >
              <link.icon size={20} />
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className="mobile-menu-footer">
          <button
            className="mobile-menu-logout"
            onClick={() => {
              closeMenu()
              onLogout()
            }}
          >
            <LogOut size={20} />
            {isDemoMode ? 'Sair do Demo' : 'Logout'}
          </button>
        </div>
      </div>
    </>
  )
}
