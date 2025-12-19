import { NavLink, useLocation } from 'react-router-dom'
import { useState, useRef, useEffect } from 'react'
import { ChevronDown, BarChart3, PiggyBank, Bot } from 'lucide-react'
import MobileMenu from './MobileMenu'

// Helper to get base path based on demo mode
function useBasePath() {
  const location = useLocation()
  return location.pathname.startsWith('/demo-app') ? '/demo-app' : '/app'
}

// Dropdown menu component
function NavDropdown({ label, icon: Icon, children, basePath }) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef(null)
  const location = useLocation()

  // Check if any child route is active
  const isChildActive = children.some(child =>
    location.pathname === `${basePath}${child.path}` ||
    location.pathname.startsWith(`${basePath}${child.path}/`)
  )

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div className="nav-dropdown" ref={dropdownRef}>
      <button
        className={`nav-link nav-dropdown-trigger ${isChildActive ? 'active' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
      >
        {Icon && <Icon size={16} />}
        <span>{label}</span>
        <ChevronDown size={14} className={`nav-dropdown-arrow ${isOpen ? 'open' : ''}`} />
      </button>
      {isOpen && (
        <div className="nav-dropdown-menu">
          {children.map(child => (
            <NavLink
              key={child.path}
              to={`${basePath}${child.path}`}
              className={({ isActive }) => `nav-dropdown-item ${isActive ? 'active' : ''}`}
              onClick={() => setIsOpen(false)}
            >
              {child.icon && <child.icon size={16} />}
              <span>{child.label}</span>
            </NavLink>
          ))}
        </div>
      )}
    </div>
  )
}

function DumontLogo() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Cloud shape */}
      <path
        d="M26 16.5C26 13.46 23.54 11 20.5 11C20.17 11 19.85 11.03 19.54 11.08C18.44 8.17 15.62 6 12.32 6C8.11 6 4.68 9.36 4.53 13.55C2.47 14.17 1 16.06 1 18.32C1 21.16 3.34 23.5 6.18 23.5H25C28.04 23.5 30.5 21.04 30.5 18C30.5 15.35 28.62 13.13 26.12 12.58"
        fill="url(#cloudGradient)"
        stroke="url(#cloudStroke)"
        strokeWidth="1.5"
      />
      {/* D letter stylized */}
      <path
        d="M10 11V20H13C15.76 20 18 17.76 18 15C18 12.24 15.76 10 13 10H10V11Z"
        fill="#0e110e"
        stroke="#4ade80"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Accent dots representing data/cloud */}
      <circle cx="22" cy="15" r="1.5" fill="#4ade80"/>
      <circle cx="24" cy="18" r="1" fill="#22c55e"/>
      <defs>
        <linearGradient id="cloudGradient" x1="1" y1="6" x2="30.5" y2="23.5" gradientUnits="userSpaceOnUse">
          <stop stopColor="#1a1f1a"/>
          <stop offset="1" stopColor="#131713"/>
        </linearGradient>
        <linearGradient id="cloudStroke" x1="1" y1="6" x2="30.5" y2="23.5" gradientUnits="userSpaceOnUse">
          <stop stopColor="#22c55e"/>
          <stop offset="1" stopColor="#4ade80"/>
        </linearGradient>
      </defs>
    </svg>
  )
}

export default function Layout({ user, onLogout, children, isDemo = false }) {
  const basePath = useBasePath()
  const isDemoMode = isDemo || basePath === '/demo-app'

  return (
    <div className="layout">
      <header className="header">
        <div className="header-left">
          {/* Mobile Menu - visível apenas em telas pequenas */}
          <MobileMenu onLogout={onLogout} basePath={basePath} />

          <div className="logo-container">
            <DumontLogo />
            <span className="logo-text">Dumont <span className="logo-highlight">Cloud</span></span>
            {isDemoMode && <span className="demo-badge">DEMO</span>}
          </div>
          <div className="header-divider desktop-only"></div>
          <nav className="nav desktop-only">
            <NavLink to={basePath} end className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              Dashboard
            </NavLink>
            <NavLink to={`${basePath}/machines`} className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              Machines
            </NavLink>
            <NavDropdown
              label="Analytics"
              icon={BarChart3}
              basePath={basePath}
              children={[
                { path: '/metrics-hub', label: 'Métricas', icon: BarChart3 },
                { path: '/savings', label: 'Economia', icon: PiggyBank },
                { path: '/advisor', label: 'AI Advisor', icon: Bot },
              ]}
            />
            <NavLink to={`${basePath}/settings`} className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              Settings
            </NavLink>
          </nav>
        </div>
        <div className="header-right">
          <span className="user-name">{user?.username}</span>
          <button className="btn btn-sm" onClick={onLogout}>{isDemoMode ? 'Sair do Demo' : 'Logout'}</button>
        </div>
      </header>
      <main className="main">
        {children}
      </main>
    </div>
  )
}
