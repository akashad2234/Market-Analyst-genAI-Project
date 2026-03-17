function getScoreColor(score) {
  if (score >= 80) return 'var(--color-strong-buy)'
  if (score >= 60) return 'var(--color-buy)'
  if (score >= 40) return 'var(--color-hold)'
  return 'var(--color-avoid)'
}

function getScoreLabel(score) {
  if (score >= 80) return 'Strong'
  if (score >= 60) return 'Good'
  if (score >= 40) return 'Moderate'
  return 'Weak'
}

export default function ScoreGauge({ score, label, size = 100 }) {
  if (score == null) return <div className="score-gauge empty">N/A</div>

  const radius = (size - 12) / 2
  const circumference = 2 * Math.PI * radius
  const progress = (score / 100) * circumference
  const color = getScoreColor(score)

  return (
    <div className="score-gauge" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--color-border)"
          strokeWidth="6"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - progress}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: 'stroke-dashoffset 0.8s ease' }}
        />
      </svg>
      <div className="score-gauge-text">
        <span className="score-value" style={{ color }}>
          {score.toFixed(0)}
        </span>
        <span className="score-sub">{label || getScoreLabel(score)}</span>
      </div>
    </div>
  )
}
