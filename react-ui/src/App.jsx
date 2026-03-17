import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import SingleStock from './pages/SingleStock'
import Portfolio from './pages/Portfolio'
import Compare from './pages/Compare'
import HistoryPage from './pages/HistoryPage'
import './App.css'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<SingleStock />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/history" element={<HistoryPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
