import { useCallback, useEffect, useState } from 'react'
import { History, RefreshCw } from 'lucide-react'
import { getHistory } from '../services/api'
import ErrorAlert from '../components/ErrorAlert'

export default function HistoryPage() {
  const [records, setRecords] = useState([])
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchHistory = useCallback(async () => {
    setLoading(true)
    setError(null)
    console.log('[History] Fetching history, filter:', filter || '(all)')
    try {
      const data = await getHistory(filter || null, 50)
      setRecords(data)
    } catch (err) {
      setError(err.message || 'Failed to load history')
    } finally {
      setLoading(false)
    }
  }, [filter])

  useEffect(() => {
    fetchHistory()
  }, [fetchHistory])

  const formatDate = (ts) => {
    if (!ts) return 'N/A'
    return new Date(ts * 1000).toLocaleString()
  }

  return (
    <div className="page">
      <div className="page-header">
        <h2>Analysis History</h2>
        <p className="page-subtitle">Past analysis results stored in the database</p>
      </div>

      <div className="history-controls">
        <div className="input-group">
          <History size={18} className="input-icon" />
          <input
            type="text"
            placeholder="Filter by ticker (optional)"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="text-input"
          />
        </div>
        <button onClick={fetchHistory} className="btn btn-secondary" disabled={loading}>
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
          Refresh
        </button>
      </div>

      <ErrorAlert message={error} onDismiss={() => setError(null)} />

      {records.length === 0 && !loading && (
        <div className="empty-state">
          <History size={48} />
          <p>No analysis history yet. Run some analyses first.</p>
        </div>
      )}

      {records.length > 0 && (
        <div className="history-table-wrapper">
          <table className="history-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Type</th>
                <th>Fund.</th>
                <th>Tech.</th>
                <th>Sent.</th>
                <th>Final</th>
                <th>Recommendation</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr key={r.id}>
                  <td className="ticker-cell">{r.ticker}</td>
                  <td>{r.query_type}</td>
                  <td>{r.fundamental_score?.toFixed(1) ?? 'N/A'}</td>
                  <td>{r.technical_score?.toFixed(1) ?? 'N/A'}</td>
                  <td>{r.sentiment_score?.toFixed(1) ?? 'N/A'}</td>
                  <td className="final-cell">
                    {r.final_score?.toFixed(1) ?? 'N/A'}
                  </td>
                  <td>{r.recommendation || 'N/A'}</td>
                  <td className="date-cell">{formatDate(r.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
