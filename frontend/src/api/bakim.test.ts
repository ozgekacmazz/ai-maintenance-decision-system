import { afterEach, describe, expect, it, vi } from 'vitest'
import { authBellekDurumunuSifirla } from './auth'
import { makineleriGetir } from './bakim'

afterEach(() => {
  authBellekDurumunuSifirla()
  vi.restoreAllMocks()
})

describe('makineleriGetir', () => {
  it('normal operasyonel seçim için minimum lookup endpointini kullanır', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          count: 1,
          next: null,
          previous: null,
          results: [{ id: 1, kod: 'M-1', ad: 'Pres', aktif: true }],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )

    const response = await makineleriGetir()

    expect(String(fetchMock.mock.calls[0][0])).toBe(
      'http://localhost:8000/api/makine-secenekleri/'
    )
    expect(response.results[0]).toEqual({ id: 1, kod: 'M-1', ad: 'Pres', aktif: true })
  })
})
