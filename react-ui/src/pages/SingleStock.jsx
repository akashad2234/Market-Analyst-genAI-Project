import { useState } from 'react'
import { Search } from 'lucide-react'
import { analyzeStock } from '../services/api'
import useAnalysis from '../hooks/useAnalysis'
import StockCard from '../components/StockCard'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorAlert from '../components/ErrorAlert'

export default function SingleStock() {
  const [ticker, setTicker] = useState('')
  const { data, loading, error, execute, reset } = useAnalysis(analyzeStock)

  const handleSubmit = (e) => {
    e.preventDefault()
    const cleaned = ticker.trim()
    if (!cleaned) return
    console.log('[SingleStock] Submitting analysis for:', cleaned)
    execute(cleaned)
  }

  return (
    <div className="page">
      <div className="page-header">
        <h2>Stock Analysis</h2>
        <p className="page-subtitle">
          Enter a ticker to get fundamental, technical, and sentiment analysis
        </p>
      </div>

      <form className="input-form" onSubmit={handleSubmit}>
        <div className="input-group">
          <Search size={18} className="input-icon" />
          <input
            type="text"
            placeholder="e.g. RELIANCE, TCS, ADANIPOWER"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            disabled={loading}
            className="text-input"
          />
        </div>
        <button type="submit" disabled={loading || !ticker.trim()} className="btn btn-primary">
          {loading ? 'Analyzing...' : 'Analyze'}
        </button>
      </form>

      <ErrorAlert message={error} onDismiss={reset} />

      {loading && <LoadingSpinner message="Running analysis pipeline..." />}

      {data && (
        <div className="results-section">
          <StockCard stock={data.stock} />
          {data.summary && (
            <div className="summary-box">
              <h4>Summary</h4>
              <p>{data.summary}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
