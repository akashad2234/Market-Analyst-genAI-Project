import { useState } from 'react'
import { GitCompare } from 'lucide-react'
import { compareStocks } from '../services/api'
import useAnalysis from '../hooks/useAnalysis'
import StockCard from '../components/StockCard'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorAlert from '../components/ErrorAlert'

export default function Compare() {
  const [stock1, setStock1] = useState('')
  const [stock2, setStock2] = useState('')
  const { data, loading, error, execute, reset } = useAnalysis(compareStocks)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!stock1.trim() || !stock2.trim()) return
    console.log('[Compare] Comparing:', stock1.trim(), 'vs', stock2.trim())
    execute(stock1.trim(), stock2.trim())
  }

  return (
    <div className="page">
      <div className="page-header">
        <h2>Compare Stocks</h2>
        <p className="page-subtitle">Compare two stocks side by side</p>
      </div>

      <form className="input-form compare-form" onSubmit={handleSubmit}>
        <div className="input-group">
          <input
            type="text"
            placeholder="Stock 1 (e.g. TATAMOTORS)"
            value={stock1}
            onChange={(e) => setStock1(e.target.value)}
            disabled={loading}
            className="text-input"
          />
        </div>
        <div className="vs-divider">
          <GitCompare size={20} />
          <span>vs</span>
        </div>
        <div className="input-group">
          <input
            type="text"
            placeholder="Stock 2 (e.g. M&M)"
            value={stock2}
            onChange={(e) => setStock2(e.target.value)}
            disabled={loading}
            className="text-input"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !stock1.trim() || !stock2.trim()}
          className="btn btn-primary"
        >
          {loading ? 'Comparing...' : 'Compare'}
        </button>
      </form>

      <ErrorAlert message={error} onDismiss={reset} />

      {loading && <LoadingSpinner message="Comparing stocks..." />}

      {data?.stocks && (
        <div className="results-section">
          {data.summary && (
            <div className="summary-box">
              <h4>Comparison Result</h4>
              <pre className="summary-pre">{data.summary}</pre>
            </div>
          )}
          <div className="compare-grid">
            {data.stocks.map((stock) => (
              <StockCard key={stock.ticker} stock={stock} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
