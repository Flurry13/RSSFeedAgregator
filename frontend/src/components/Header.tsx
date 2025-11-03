import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Globe, Rss, Languages, BarChart3 } from 'lucide-react'

const Header: React.FC = () => {
  const location = useLocation()

  const navItems = [
    { path: '/', label: 'Dashboard', icon: BarChart3 },
    { path: '/feeds', label: 'Feeds', icon: Rss },
    { path: '/translations', label: 'Translations', icon: Languages },
  ]

  return (
    <header className="backdrop-blur-xl bg-white/5 border-b border-white/10 shadow-2xl sticky top-0 z-50">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-3">
            <div className="relative">
              <Globe className="h-8 w-8 text-blue-400 drop-shadow-[0_0_10px_rgba(59,130,246,0.5)]" />
              <div className="absolute inset-0 blur-xl bg-blue-500/30 -z-10"></div>
            </div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 via-cyan-400 to-blue-500 bg-clip-text text-transparent drop-shadow-lg">
              Vastwick News Aggregator
            </h1>
          </div>
          
          <nav className="flex space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.path
              
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300 ${
                    isActive
                      ? 'bg-gradient-to-r from-blue-500/30 to-cyan-500/30 text-blue-300 border border-blue-400/30 shadow-lg shadow-blue-500/20'
                      : 'text-gray-300 hover:text-white hover:bg-white/10 border border-transparent hover:border-white/20'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </Link>
              )
            })}
          </nav>
        </div>
      </div>
    </header>
  )
}

export default Header 