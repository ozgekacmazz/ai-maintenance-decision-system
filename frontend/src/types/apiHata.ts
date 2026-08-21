export type AlanHatalari = Record<string, unknown>

export interface ApiHataGovdesi {
  hata: {
    kod: string
    mesaj: string
    alanlar: AlanHatalari
    trace_id: string
  }
}

export class ApiHatasi extends Error {
  constructor(
    public readonly status: number,
    public readonly kod: string,
    mesaj: string,
    public readonly alanlar: AlanHatalari = {},
    public readonly traceId?: string,
  ) {
    super(status >= 500 && traceId
      ? `${mesaj} Hata devam ederse destek ekibine şu takip kodunu iletin: ${traceId}`
      : mesaj)
    this.name = 'ApiHatasi'
  }
}

export async function responseHatasiniNormalizeEt(response: Response): Promise<ApiHatasi> {
  try {
    const data = await response.clone().json() as Partial<ApiHataGovdesi>
    if (data.hata?.kod && data.hata.mesaj) {
      return new ApiHatasi(
        response.status,
        data.hata.kod,
        data.hata.mesaj,
        data.hata.alanlar ?? {},
        data.hata.trace_id,
      )
    }
  } catch {
    // Güvenli fallback aşağıda oluşturulur.
  }
  return new ApiHatasi(
    response.status,
    'BEKLENMEYEN_YANIT',
    response.status === 429
      ? 'Çok fazla istek gönderildi. Lütfen kısa süre sonra tekrar deneyin.'
      : 'İstek tamamlanamadı. Lütfen tekrar deneyin.',
  )
}

export function agHatasiniNormalizeEt(): ApiHatasi {
  return new ApiHatasi(
    0,
    'BAGLANTI_HATASI',
    'Sunucuya bağlanılamadı. Bağlantınızı kontrol edip tekrar deneyin.',
  )
}

export type DuzAlanHatalari = Record<string, string[]>

function hataMesajlariniTopla(deger: unknown): string[] {
  if (typeof deger === 'string') return [deger]
  if (typeof deger === 'number' || typeof deger === 'boolean') return [String(deger)]
  if (Array.isArray(deger)) return deger.flatMap(hataMesajlariniTopla)
  return []
}

/** API'nin iç içe doğrulama gövdesini noktalı alan yollarına dönüştürür. */
export function alanHatalariniDuzlestir(
  alanlar: unknown,
  ustYol = '',
  sonuc: DuzAlanHatalari = {},
): DuzAlanHatalari {
  if (alanlar === null || alanlar === undefined) return sonuc
  const dogrudanMesajlar = hataMesajlariniTopla(alanlar)
  if (dogrudanMesajlar.length > 0 && ustYol) {
    sonuc[ustYol] = [...(sonuc[ustYol] ?? []), ...dogrudanMesajlar]
    return sonuc
  }
  if (typeof alanlar !== 'object') return sonuc

  Object.entries(alanlar as Record<string, unknown>).forEach(([anahtar, deger]) => {
    const yol = ustYol ? `${ustYol}.${anahtar}` : anahtar
    alanHatalariniDuzlestir(deger, yol, sonuc)
  })
  return sonuc
}

export function alanHatasiGetir(
  hata: ApiHatasi | null | undefined,
  alan: string,
  ...apiYollari: string[]
): string | null {
  if (!hata) return null
  const duz = alanHatalariniDuzlestir(hata.alanlar)
  const yollar = [alan, ...apiYollari]
  const tamEslesme = yollar.find((yol) => duz[yol]?.length)
  if (tamEslesme) return duz[tamEslesme].join(' ')
  const sonEk = yollar.find((yol) => {
    const kisa = yol.split('.').at(-1)
    return Object.keys(duz).some((aday) => aday.split('.').at(-1) === kisa)
  })
  if (!sonEk) return null
  const kisa = sonEk.split('.').at(-1)
  const eslesen = Object.keys(duz).find((aday) => aday.split('.').at(-1) === kisa)
  return eslesen ? duz[eslesen].join(' ') : null
}

export function ilkHataliAlanaOdaklan(hatalar: DuzAlanHatalari) {
  const ilkAlan = Object.keys(hatalar)[0]?.split('.').at(-1)
  if (!ilkAlan) return
  requestAnimationFrame(() => {
    const eleman = document.querySelector<HTMLElement>(
      `[name="${CSS.escape(ilkAlan)}"], #${CSS.escape(ilkAlan)}`,
    )
    eleman?.focus()
    eleman?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  })
}
