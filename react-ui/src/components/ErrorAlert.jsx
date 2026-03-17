import { AlertTriangle } from 'lucide-react'

export default function ErrorAlert({ message, onDismiss }) {
  if (!message) return null

  return (
    <div className="error-alert" role="alert">
      <AlertTriangle size={18} />
      <span>{message}</span>
      {onDismiss && (
        <button className="error-dismiss" onClick={onDismiss}>
          &times;
        </button>
      )}
    </div>
  )
}
