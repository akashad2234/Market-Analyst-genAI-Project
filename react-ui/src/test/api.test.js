import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import {
  analyzeStock,
  analyzePortfolio,
  compareStocks,
  getHealth,
  getHistory,
  getCacheStats,
} from '../services/api'

vi.mock('axios', () => {
  const mockClient = {
    get: vi.fn(),
    post: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  }
  return {
    default: { create: vi.fn(() => mockClient), ...mockClient },
    __mockClient: mockClient,
  }
})

const mockClient = axios.create()

beforeEach(() => {
  vi.clearAllMocks()
})

describe('API Service', () => {
  it('analyzeStock sends POST with ticker', async () => {
    const mockResponse = {
      data: { stock: { ticker: 'RELIANCE.NS', final_score: 72 }, summary: '' },
    }
    mockClient.post.mockResolvedValueOnce(mockResponse)

    const result = await analyzeStock('RELIANCE')
    expect(mockClient.post).toHaveBeenCalledWith('/analyze_stock', {
      ticker: 'RELIANCE',
    })
    expect(result.stock.ticker).toBe('RELIANCE.NS')
  })

  it('analyzePortfolio sends POST with stocks array', async () => {
    const mockResponse = {
      data: { stocks: [], summary: '', portfolio_insight: null },
    }
    mockClient.post.mockResolvedValueOnce(mockResponse)

    await analyzePortfolio(['TCS', 'INFY'])
    expect(mockClient.post).toHaveBeenCalledWith('/portfolio_analysis', {
      stocks: ['TCS', 'INFY'],
    })
  })

  it('compareStocks sends POST with stock1 and stock2', async () => {
    const mockResponse = { data: { stocks: [], summary: '' } }
    mockClient.post.mockResolvedValueOnce(mockResponse)

    await compareStocks('TCS', 'INFY')
    expect(mockClient.post).toHaveBeenCalledWith('/compare_stocks', {
      stock1: 'TCS',
      stock2: 'INFY',
    })
  })

  it('getHealth calls GET /health', async () => {
    mockClient.get.mockResolvedValueOnce({
      data: { status: 'ok', version: '0.1.0' },
    })

    const result = await getHealth()
    expect(mockClient.get).toHaveBeenCalledWith('/health')
    expect(result.status).toBe('ok')
  })

  it('getHistory calls GET /history with params', async () => {
    mockClient.get.mockResolvedValueOnce({ data: [] })

    await getHistory('TCS.NS', 10)
    expect(mockClient.get).toHaveBeenCalledWith('/history', {
      params: { ticker: 'TCS.NS', limit: 10 },
    })
  })

  it('getHistory without ticker omits ticker param', async () => {
    mockClient.get.mockResolvedValueOnce({ data: [] })

    await getHistory(null, 20)
    expect(mockClient.get).toHaveBeenCalledWith('/history', {
      params: { limit: 20 },
    })
  })

  it('getCacheStats calls GET /cache/stats', async () => {
    mockClient.get.mockResolvedValueOnce({
      data: { total: 5, expired: 1, by_source: {} },
    })

    const result = await getCacheStats()
    expect(result.total).toBe(5)
  })
})
