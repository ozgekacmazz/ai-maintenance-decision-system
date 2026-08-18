import { describe, expect, it } from 'vitest'

import { ApiHatasi, agHatasiniNormalizeEt, responseHatasiniNormalizeEt } from './apiHata'

describe('API hata normalizasyonu', () => {
  it('standart 400 alan hatalarını korur', async () => {
    const response = new Response(JSON.stringify({
      hata: { kod: 'GECERSIZ_ISTEK', mesaj: 'Doğrulama hatası.', alanlar: { username: ['Zorunlu.'] }, trace_id: 'trace-1' },
    }), { status: 400 })
    const hata = await responseHatasiniNormalizeEt(response)
    expect(hata).toBeInstanceOf(ApiHatasi)
    expect(hata.alanlar.username).toEqual(['Zorunlu.'])
  })

  it('403 ile oturum hatasını birbirinden ayırır', async () => {
    const hata = await responseHatasiniNormalizeEt(new Response(JSON.stringify({
      hata: { kod: 'YETKI_YETERSIZ', mesaj: 'Yetki yok.', alanlar: {}, trace_id: 'trace-2' },
    }), { status: 403 }))
    expect(hata.status).toBe(403)
    expect(hata.kod).toBe('YETKI_YETERSIZ')
  })

  it('429 için güvenli mesaj üretir', async () => {
    const hata = await responseHatasiniNormalizeEt(new Response('not-json', { status: 429 }))
    expect(hata.message).toContain('Çok fazla istek')
  })

  it('500 mesajına trace referansı ekler', async () => {
    const hata = await responseHatasiniNormalizeEt(new Response(JSON.stringify({
      hata: { kod: 'BEKLENMEYEN_SUNUCU_HATASI', mesaj: 'Beklenmeyen hata.', alanlar: {}, trace_id: 'trace-500' },
    }), { status: 500 }))
    expect(hata.message).toContain('trace-500')
  })

  it('JSON olmayan yanıt ve ağ hatası için fallback sağlar', async () => {
    expect((await responseHatasiniNormalizeEt(new Response('<html>', { status: 502 }))).kod).toBe('BEKLENMEYEN_YANIT')
    expect(agHatasiniNormalizeEt().kod).toBe('BAGLANTI_HATASI')
  })
})
