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
