import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

const client = axios.create({
  baseURL: API_BASE,
  timeout: 120_000,
  headers: { 'Content-Type': 'application/json' },
})

client.interceptors.request.use((config) => {
  console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`, config.data ?? '')
  return config
})

client.interceptors.response.use(
  (response) => {
    console.log(`[API] Response ${response.status} from ${response.config.url}`)
    return response
  },
  (error) => {
    console.error(`[API] Error from ${error.config?.url}:`, error.message)
    return Promise.reject(error)
  },
)

export async function analyzeStock(ticker) {
  const { data } = await client.post('/analyze_stock', { ticker })
  return data
}

export async function analyzePortfolio(stocks) {
  const { data } = await client.post('/portfolio_analysis', { stocks })
  return data
}

export async function compareStocks(stock1, stock2) {
  const { data } = await client.post('/compare_stocks', { stock1, stock2 })
  return data
}

export async function getHealth() {
  const { data } = await client.get('/health')
  return data
}

export async function getHistory(ticker = null, limit = 20) {
  const params = { limit }
  if (ticker) params.ticker = ticker
  const { data } = await client.get('/history', { params })
  return data
}

export async function getCacheStats() {
  const { data } = await client.get('/cache/stats')
  return data
}

export default client
