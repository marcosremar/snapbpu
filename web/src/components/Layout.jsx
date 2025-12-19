import { NavLink } from 'react-router-dom'
import MobileMenu from './MobileMenu'

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

export default function Layout({ user, onLogout, children }) {
  return (
    <div className="layout">
      <header className="header">
        <div className="header-left">
          {/* Mobile Menu - visível apenas em telas pequenas */}
          <MobileMenu onLogout={onLogout} />

          <div className="logo-container">
            <DumontLogo />
            <span className="logo-text">Dumont <span className="logo-highlight">Cloud</span></span>
          </div>
          <div className="header-divider desktop-only"></div>
          <nav className="nav desktop-only">
            <NavLink to="/app" end className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              Dashboard
            </NavLink>
            <NavLink to="/app/machines" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              Machines
            </NavLink>
            <NavLink to="/app/advisor" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              AI Advisor
            </NavLink>
            <NavLink to="/app/metrics-hub" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              Métricas
            </NavLink>
            <NavLink to="/app/savings" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              Economia
            </NavLink>
            <NavLink to="/app/settings" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              Settings
            </NavLink>
          </nav>
        </div>
        <div className="header-right">
          <span className="user-name">{user?.username}</span>
          <button className="btn btn-sm" onClick={onLogout}>Logout</button>
        </div>
      </header>
      <main className="main">
        {children}
      </main>
    </div>
  )
}
