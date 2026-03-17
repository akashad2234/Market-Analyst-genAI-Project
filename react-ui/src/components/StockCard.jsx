import ScoreGauge from './ScoreGauge'

function getBadgeClass(recommendation) {
  const r = (recommendation || '').toLowerCase()
  if (r.includes('strong buy')) return 'badge badge-strong-buy'
  if (r.includes('buy')) return 'badge badge-buy'
  if (r.includes('hold')) return 'badge badge-hold'
  return 'badge badge-avoid'
}

export default function StockCard({ stock, compact = false }) {
  if (!stock) return null

  return (
    <div className={`stock-card ${compact ? 'compact' : ''}`}>
      <div className="stock-card-header">
        <h3 className="stock-ticker">{stock.ticker}</h3>
        <span className={getBadgeClass(stock.recommendation)}>
          {stock.recommendation || 'N/A'}
        </span>
      </div>

      <div className="score-row">
        <div className="score-item">
          <ScoreGauge
            score={stock.fundamental_score}
            label={stock.fundamental_verdict}
            size={compact ? 72 : 90}
          />
          <span className="score-label">Fundamental</span>
        </div>
        <div className="score-item">
          <ScoreGauge
            score={stock.technical_score}
            label={stock.technical_verdict}
            size={compact ? 72 : 90}
          />
          <span className="score-label">Technical</span>
        </div>
        <div className="score-item">
          <ScoreGauge
            score={stock.sentiment_score}
            label={stock.sentiment_verdict}
            size={compact ? 72 : 90}
          />
          <span className="score-label">Sentiment</span>
        </div>
        <div className="score-item final">
          <ScoreGauge
            score={stock.final_score}
            label="Final"
            size={compact ? 80 : 100}
          />
          <span className="score-label">Overall</span>
        </div>
      </div>

      {!compact && stock.explanation && (
        <div className="stock-explanation">
          <p>{stock.explanation}</p>
        </div>
      )}

      {Object.keys(stock.errors || {}).length > 0 && (
        <div className="stock-errors">
          {Object.entries(stock.errors).map(([agent, msg]) => (
            <p key={agent} className="error-line">
              <strong>{agent}:</strong> {msg}
            </p>
          ))}
        </div>
      )}
    </div>
  )
}
