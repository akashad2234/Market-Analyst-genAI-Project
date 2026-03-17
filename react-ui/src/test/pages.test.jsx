import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import SingleStock from '../pages/SingleStock'
import Compare from '../pages/Compare'
import Portfolio from '../pages/Portfolio'

vi.mock('../services/api', () => ({
  analyzeStock: vi.fn(),
  analyzePortfolio: vi.fn(),
  compareStocks: vi.fn(),
  getHistory: vi.fn(),
  getCacheStats: vi.fn(),
}))

import { analyzeStock, analyzePortfolio, compareStocks } from '../services/api'

function renderWithRouter(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

describe('SingleStock Page', () => {
  it('renders the form', () => {
    renderWithRouter(<SingleStock />)
    expect(screen.getByText('Stock Analysis')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/RELIANCE/)).toBeInTheDocument()
    expect(screen.getByText('Analyze')).toBeInTheDocument()
  })

  it('disables button when input is empty', () => {
    renderWithRouter(<SingleStock />)
    const button = screen.getByText('Analyze')
    expect(button).toBeDisabled()
  })

  it('enables button when input has value', () => {
    renderWithRouter(<SingleStock />)
    const input = screen.getByPlaceholderText(/RELIANCE/)
    fireEvent.change(input, { target: { value: 'TCS' } })
    expect(screen.getByText('Analyze')).not.toBeDisabled()
  })

  it('calls analyzeStock on form submit', async () => {
    const mockResult = {
      stock: {
        ticker: 'TCS.NS',
        fundamental_score: 70,
        fundamental_verdict: 'Strong',
        technical_score: 60,
        technical_verdict: 'Moderate',
        sentiment_score: 65,
        sentiment_verdict: 'Positive',
        final_score: 65,
        recommendation: 'Buy',
        explanation: '',
        errors: {},
      },
      summary: 'TCS: Buy',
    }
    analyzeStock.mockResolvedValueOnce(mockResult)

    renderWithRouter(<SingleStock />)
    const input = screen.getByPlaceholderText(/RELIANCE/)
    fireEvent.change(input, { target: { value: 'TCS' } })
    fireEvent.click(screen.getByText('Analyze'))

    await waitFor(() => {
      expect(analyzeStock).toHaveBeenCalledWith('TCS')
    })
  })

  it('shows results after successful analysis', async () => {
    analyzeStock.mockResolvedValueOnce({
      stock: {
        ticker: 'TCS.NS',
        fundamental_score: 70,
        fundamental_verdict: 'Strong',
        technical_score: 60,
        technical_verdict: 'Moderate',
        sentiment_score: 65,
        sentiment_verdict: 'Positive',
        final_score: 65,
        recommendation: 'Buy',
        explanation: '',
        errors: {},
      },
      summary: 'TCS is a Buy',
    })

    renderWithRouter(<SingleStock />)
    fireEvent.change(screen.getByPlaceholderText(/RELIANCE/), {
      target: { value: 'TCS' },
    })
    fireEvent.click(screen.getByText('Analyze'))

    await waitFor(() => {
      expect(screen.getByText('TCS.NS')).toBeInTheDocument()
      expect(screen.getByText('Buy')).toBeInTheDocument()
    })
  })
})

describe('Compare Page', () => {
  it('renders two input fields and vs divider', () => {
    renderWithRouter(<Compare />)
    expect(screen.getByText('Compare Stocks')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Stock 1/)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Stock 2/)).toBeInTheDocument()
    expect(screen.getByText('vs')).toBeInTheDocument()
  })

  it('disables button when inputs are empty', () => {
    renderWithRouter(<Compare />)
    expect(screen.getByText('Compare')).toBeDisabled()
  })

  it('calls compareStocks on submit', async () => {
    compareStocks.mockResolvedValueOnce({ stocks: [], summary: '' })

    renderWithRouter(<Compare />)
    fireEvent.change(screen.getByPlaceholderText(/Stock 1/), {
      target: { value: 'TCS' },
    })
    fireEvent.change(screen.getByPlaceholderText(/Stock 2/), {
      target: { value: 'INFY' },
    })
    fireEvent.click(screen.getByText('Compare'))

    await waitFor(() => {
      expect(compareStocks).toHaveBeenCalledWith('TCS', 'INFY')
    })
  })
})

describe('Portfolio Page', () => {
  it('renders the form', () => {
    renderWithRouter(<Portfolio />)
    expect(screen.getByText('Portfolio Analysis')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/RELIANCE, TCS/)).toBeInTheDocument()
  })

  it('calls analyzePortfolio on submit', async () => {
    analyzePortfolio.mockResolvedValueOnce({
      stocks: [],
      summary: '',
      portfolio_insight: null,
    })

    renderWithRouter(<Portfolio />)
    fireEvent.change(screen.getByPlaceholderText(/RELIANCE, TCS/), {
      target: { value: 'TCS, INFY' },
    })
    fireEvent.click(screen.getByText('Analyze Portfolio'))

    await waitFor(() => {
      expect(analyzePortfolio).toHaveBeenCalledWith(['TCS', 'INFY'])
    })
  })
})
