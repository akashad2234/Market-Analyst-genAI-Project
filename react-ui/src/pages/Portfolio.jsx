import { useState } from 'react'
import { LineChart } from 'lucide-react'
import { analyzePortfolio } from '../services/api'
import useAnalysis from '../hooks/useAnalysis'
import StockCard from '../components/StockCard'
import ScoreGauge from '../components/ScoreGauge'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorAlert from '../components/ErrorAlert'

export default function Portfolio() {
  const [input, setInput] = useState('')
  const { data, loading, error, execute, reset } = useAnalysis(analyzePortfolio)

  const handleSubmit = (e) => {
    e.preventDefault()
    const stocks = input
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    if (stocks.length < 2) return
    console.log('[Portfolio] Submitting portfolio analysis:', stocks)
    execute(stocks)
  }

  const insight = data?.portfolio_insight

  return (
    <div className="page">
      <div className="page-header">
        <h2>Portfolio Analysis</h2>
        <p className="page-subtitle">
          Enter comma-separated tickers (minimum 2)
        </p>
      </div>

      <form className="input-form" onSubmit={handleSubmit}>
        <div className="input-group">
          <LineChart size={18} className="input-icon" />
          <input
            type="text"
            placeholder="e.g. RELIANCE, TCS, INFY, TATAMOTORS"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            className="text-input"
          />
        </div>
        <button type="submit" disabled={loading || !input.trim()} className="btn btn-primary">
          {loading ? 'Analyzing...' : 'Analyze Portfolio'}
        </button>
      </form>

      <ErrorAlert message={error} onDismiss={reset} />

      {loading && (
        <LoadingSpinner message="Analyzing portfolio (this may take a minute)..." />
      )}

      {insight && (
        <div className="portfolio-insight">
          <h3>Portfolio Overview</h3>
          <div className="insight-grid">
            <div className="insight-card">
              <ScoreGauge score={insight.average_score} label="Avg Score" size={90} />
            </div>
            <div className="insight-card">
              <div className="insight-stat">
                <span className="stat-label">Overall Risk</span>
                <span className={`stat-value risk-${insight.overall_risk?.toLowerCase()}`}>
                  {insight.overall_risk}
                </span>
              </div>
            </div>
            <div className="insight-card">
              <div className="insight-stat">
                <span className="stat-label">Best Performer</span>
                <span className="stat-value">{insight.best_performer}</span>
              </div>
            </div>
            <div className="insight-card">
              <div className="insight-stat">
                <span className="stat-label">Diversification</span>
                <span className="stat-value">
                  {insight.diversification_score?.toFixed(1)}/100
                </span>
              </div>
            </div>
          </div>
          {insight.rebalance_suggestion && (
            <div className="summary-box">
              <h4>Rebalance Suggestion</h4>
              <p>{insight.rebalance_suggestion}</p>
            </div>
          )}
        </div>
      )}

      {data?.stocks && (
        <div className="results-section">
          <h3>Individual Stocks</h3>
          <div className="stock-grid">
            {data.stocks.map((stock) => (
              <StockCard key={stock.ticker} stock={stock} compact />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
