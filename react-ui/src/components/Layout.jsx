import { NavLink, Outlet } from 'react-router-dom'
import { BarChart3, GitCompare, LineChart, History } from 'lucide-react'

const NAV_ITEMS = [
  { to: '/', label: 'Stock Analysis', icon: BarChart3 },
  { to: '/portfolio', label: 'Portfolio', icon: LineChart },
  { to: '/compare', label: 'Compare', icon: GitCompare },
  { to: '/history', label: 'History', icon: History },
]

export default function Layout() {
  return (
    <div className="app-layout">
      <nav className="sidebar">
        <div className="sidebar-brand">
          <BarChart3 size={28} />
          <h1>Market Analyst</h1>
        </div>
        <ul className="nav-list">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <li key={to}>
              <NavLink
                to={to}
                className={({ isActive }) =>
                  `nav-link ${isActive ? 'active' : ''}`
                }
              >
                <Icon size={18} />
                <span>{label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
        <div className="sidebar-footer">
          <span className="version-tag">v0.1.0</span>
        </div>
      </nav>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}
