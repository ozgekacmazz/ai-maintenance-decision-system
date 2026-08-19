import { afterEach, describe, expect, it, vi } from 'vitest'

import { authBellekDurumunuSifirla } from './auth'
import { inputDomainContractGetir, tahminKayitlariniGetir, tahminLoglariniGetir, tahminReddet } from './tahminler'
import { ApiHatasi } from '../types/apiHata'

afterEach(() => {
  authBellekDurumunuSifirla()
  vi.restoreAllMocks()
})

describe('inputDomainContractGetir', () => {
  it('kimlikli, salt okunur sözleşme endpointini çağırır', async () => {
    const body = { contract_version: 'v1', fields: {} }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } })
    )
    await expect(inputDomainContractGetir()).resolves.toEqual(body)
    expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/api/tahminler/input-domain/')
    expect(fetchMock.mock.calls[0][1]?.method).toBeUndefined()
  })
})

describe('tahminReddet', () => {
  it('doğru endpoint ve JSON body ile reddetme isteği gönderir', async () => {
    const responseBody = { id: 'tahmin-1', red_bilgisi: null }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(responseBody), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      })
    )

    await tahminReddet('tahmin-1', 'Yanlış alarm')

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][0]).toBe(
      'http://localhost:8000/api/tahminler/kayitlar/tahmin-1/reddet/'
    )
    const options = fetchMock.mock.calls[0][1]
    expect(options?.method).toBe('POST')
    expect((options?.headers as Headers).get('Content-Type')).toBe('application/json')
    expect(options?.body).toBe(JSON.stringify({ red_nedeni: 'Yanlış alarm' }))
  })

  it('standart backend hatasını ApiHatasi alanlarına dönüştürür', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          hata: {
            kod: 'TAHMIN_ZATEN_REDDEDILMIS',
            mesaj: 'Tahmin zaten reddedilmiş.',
            alanlar: { red_nedeni: ['Geçersiz neden.'] },
            trace_id: 'reject-trace-1',
          },
        }),
        { status: 409, headers: { 'Content-Type': 'application/json' } }
      )
    )

    const hata = await tahminReddet('tahmin-1', '').catch((error: unknown) => error)

    expect(hata).toBeInstanceOf(ApiHatasi)
    expect(hata).toMatchObject({
      status: 409,
      kod: 'TAHMIN_ZATEN_REDDEDILMIS',
      message: 'Tahmin zaten reddedilmiş.',
      alanlar: { red_nedeni: ['Geçersiz neden.'] },
      traceId: 'reject-trace-1',
    })
  })
})

describe('tahminKayitlariniGetir', () => {
  it('canonical filtre ve sıralamayı query parametrelerine ekler', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ count: 0, next: null, previous: null, results: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    )

    await tahminKayitlariniGetir({ genel_oncelik: 3, sirala: '-genel_oncelik' })

    const url = String(fetchMock.mock.calls[0][0])
    expect(url).toContain('genel_oncelik=3')
    expect(url).toContain('sirala=-genel_oncelik')
  })

  it('undefined canonical filtre için gereksiz query parametresi üretmez', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ count: 0, next: null, previous: null, results: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    )

    await tahminKayitlariniGetir({ genel_oncelik: undefined })

    expect(String(fetchMock.mock.calls[0][0])).toBe(
      'http://localhost:8000/api/tahminler/kayitlar/'
    )
  })
})

describe('tahminLoglariniGetir', () => {
  it('admin log endpointine yalnız dolu filtreleri encode ederek gönderir', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ count: 0, next: null, previous: null, results: [] }), {
        status: 200, headers: { 'Content-Type': 'application/json' },
      })
    )

    await tahminLoglariniGetir({ karar_durumu: 'ONAYLANDI', genel_oncelik: 5, baslangic: undefined })

    const url = String(fetchMock.mock.calls[0][0])
    expect(url).toContain('/api/tahminler/loglari/?')
    expect(url).toContain('karar_durumu=ONAYLANDI')
    expect(url).toContain('genel_oncelik=5')
    expect(url).not.toContain('baslangic')
  })
})
