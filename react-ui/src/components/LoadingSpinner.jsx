export default function LoadingSpinner({ message = 'Analyzing...' }) {
  return (
    <div className="loading-container">
      <div className="spinner" />
      <p className="loading-message">{message}</p>
    </div>
  )
}
