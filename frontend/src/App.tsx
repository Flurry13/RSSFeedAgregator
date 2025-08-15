import React from 'react'
import { Routes, Route } from 'react-router-dom'
import Header from './components/Header'
import Dashboard from './pages/Dashboard'
import Feeds from './pages/Feeds'
import Translations from './pages/Translations'
import { HeadlinesProvider } from './context/HeadlinesContext'

function App() {
  return (
    <HeadlinesProvider>
      <div className="min-h-screen bg-gray-50">
        <Header />
        <main className="container mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/feeds" element={<Feeds />} />
            <Route path="/translations" element={<Translations />} />
          </Routes>
        </main>
      </div>
    </HeadlinesProvider>
  )
}

export default App 