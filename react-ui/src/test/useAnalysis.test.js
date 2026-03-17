import { describe, it, expect, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import useAnalysis from '../hooks/useAnalysis'

describe('useAnalysis hook', () => {
  it('starts with null data and no loading', () => {
    const { result } = renderHook(() => useAnalysis(vi.fn()))
    expect(result.current.data).toBeNull()
    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('sets loading true during execution', async () => {
    let resolvePromise
    const apiFn = vi.fn(
      () => new Promise((resolve) => { resolvePromise = resolve }),
    )
    const { result } = renderHook(() => useAnalysis(apiFn))

    let promise
    act(() => {
      promise = result.current.execute('arg1')
    })
    expect(result.current.loading).toBe(true)

    await act(async () => {
      resolvePromise({ success: true })
      await promise
    })
    expect(result.current.loading).toBe(false)
    expect(result.current.data).toEqual({ success: true })
  })

  it('sets error on failure', async () => {
    const apiFn = vi.fn().mockRejectedValueOnce(new Error('Network error'))
    const { result } = renderHook(() => useAnalysis(apiFn))

    await act(async () => {
      await result.current.execute()
    })

    expect(result.current.error).toBe('Network error')
    expect(result.current.data).toBeNull()
  })

  it('extracts detail from API error response', async () => {
    const apiFn = vi.fn().mockRejectedValueOnce({
      response: { data: { detail: 'Ticker not found' } },
    })
    const { result } = renderHook(() => useAnalysis(apiFn))

    await act(async () => {
      await result.current.execute()
    })

    expect(result.current.error).toBe('Ticker not found')
  })

  it('reset clears all state', async () => {
    const apiFn = vi.fn().mockResolvedValueOnce({ value: 1 })
    const { result } = renderHook(() => useAnalysis(apiFn))

    await act(async () => {
      await result.current.execute()
    })
    expect(result.current.data).toEqual({ value: 1 })

    act(() => {
      result.current.reset()
    })
    expect(result.current.data).toBeNull()
    expect(result.current.error).toBeNull()
    expect(result.current.loading).toBe(false)
  })
})
