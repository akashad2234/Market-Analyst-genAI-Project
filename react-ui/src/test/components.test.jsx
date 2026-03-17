import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ScoreGauge from '../components/ScoreGauge'
import StockCard from '../components/StockCard'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorAlert from '../components/ErrorAlert'

describe('ScoreGauge', () => {
  it('renders score value', () => {
    render(<ScoreGauge score={75} label="Strong" />)
    expect(screen.getByText('75')).toBeInTheDocument()
    expect(screen.getByText('Strong')).toBeInTheDocument()
  })

  it('renders N/A for null score', () => {
    render(<ScoreGauge score={null} />)
    expect(screen.getByText('N/A')).toBeInTheDocument()
  })

  it('applies green color for high scores', () => {
    render(<ScoreGauge score={85} />)
    const value = screen.getByText('85')
    expect(value.style.color).toContain('--color-strong-buy')
  })
})

describe('StockCard', () => {
  const mockStock = {
    ticker: 'RELIANCE.NS',
    fundamental_score: 75,
    fundamental_verdict: 'Strong',
    technical_score: 60,
    technical_verdict: 'Moderate',
    sentiment_score: 70,
    sentiment_verdict: 'Positive',
    final_score: 68.5,
    recommendation: 'Buy',
    explanation: 'Test explanation text',
    errors: {},
  }

  it('renders ticker and recommendation', () => {
    render(<StockCard stock={mockStock} />)
    expect(screen.getByText('RELIANCE.NS')).toBeInTheDocument()
    expect(screen.getByText('Buy')).toBeInTheDocument()
  })

  it('renders all four score gauges', () => {
    render(<StockCard stock={mockStock} />)
    expect(screen.getByText('Fundamental')).toBeInTheDocument()
    expect(screen.getByText('Technical')).toBeInTheDocument()
    expect(screen.getByText('Sentiment')).toBeInTheDocument()
    expect(screen.getByText('Overall')).toBeInTheDocument()
  })

  it('renders explanation when not compact', () => {
    render(<StockCard stock={mockStock} />)
    expect(screen.getByText('Test explanation text')).toBeInTheDocument()
  })

  it('hides explanation when compact', () => {
    render(<StockCard stock={mockStock} compact />)
    expect(screen.queryByText('Test explanation text')).not.toBeInTheDocument()
  })

  it('renders errors when present', () => {
    const stockWithErrors = {
      ...mockStock,
      errors: { fundamental: 'API timeout' },
    }
    render(<StockCard stock={stockWithErrors} />)
    expect(screen.getByText('API timeout')).toBeInTheDocument()
  })

  it('returns null when stock is null', () => {
    const { container } = render(<StockCard stock={null} />)
    expect(container.firstChild).toBeNull()
  })
})

describe('LoadingSpinner', () => {
  it('renders default message', () => {
    render(<LoadingSpinner />)
    expect(screen.getByText('Analyzing...')).toBeInTheDocument()
  })

  it('renders custom message', () => {
    render(<LoadingSpinner message="Processing..." />)
    expect(screen.getByText('Processing...')).toBeInTheDocument()
  })
})

describe('ErrorAlert', () => {
  it('renders error message', () => {
    render(<ErrorAlert message="Something went wrong" />)
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
  })

  it('renders nothing when message is null', () => {
    const { container } = render(<ErrorAlert message={null} />)
    expect(container.firstChild).toBeNull()
  })

  it('has dismiss button when onDismiss provided', () => {
    render(<ErrorAlert message="Error" onDismiss={() => {}} />)
    expect(screen.getByText('×')).toBeInTheDocument()
  })
})
