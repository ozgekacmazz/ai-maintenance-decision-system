import { afterEach, describe, expect, it, vi } from 'vitest'

import { accessTokeniAyarla, authBellekDurumunuSifirla, kimlikliIstek } from './auth'

afterEach(() => {
  authBellekDurumunuSifirla()
  vi.restoreAllMocks()
})

describe('kimlikliIstek', () => {
  it('Bearer access token gönderir', async () => {
    accessTokeniAyarla('memory-token')
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{}'))
    await kimlikliIstek('/korumali/')
    const headers = fetchMock.mock.calls[0][1]?.headers as Headers
    expect(headers.get('Authorization')).toBe('Bearer memory-token')
  })

  it('401 sonrası bir refresh ve bir retry yapar', async () => {
    accessTokeniAyarla('eski')
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response('{}', { status: 401 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ csrf_token: 'csrf' })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ access: 'yeni' })))
      .mockResolvedValueOnce(new Response('{}', { status: 200 }))
    const response = await kimlikliIstek('/korumali/')
    expect(response.status).toBe(200)
    expect(fetchMock).toHaveBeenCalledTimes(4)
  })

  it('eşzamanlı 401 yanıtlarında tek refresh yürütür', async () => {
    accessTokeniAyarla('eski')
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response('{}', { status: 401 }))
      .mockResolvedValueOnce(new Response('{}', { status: 401 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ csrf_token: 'csrf' })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ access: 'yeni' })))
      .mockResolvedValue(new Response('{}', { status: 200 }))
    await Promise.all([kimlikliIstek('/a/'), kimlikliIstek('/b/')])
    const refreshCalls = fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/api/auth/refresh/'))
    expect(refreshCalls).toHaveLength(1)
  })
})
