import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { Menu, X, Home, Server, Settings, BarChart3, LogOut } from 'lucide-react'

export default function MobileMenu({ onLogout }) {
  const [isOpen, setIsOpen] = useState(false)

  const links = [
    { to: '/app', icon: Home, label: 'Dashboard' },
    { to: '/app/machines', icon: Server, label: 'Machines' },
    { to: '/app/metrics-hub', icon: BarChart3, label: 'Métricas' },
    { to: '/app/settings', icon: Settings, label: 'Settings' },
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
          {links.map(link => (
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
            Logout
          </button>
        </div>
      </div>
    </>
  )
}
