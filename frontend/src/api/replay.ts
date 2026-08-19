import { kimlikliIstek } from './auth'
import { responseHatasiniNormalizeEt } from '../types/apiHata'
import type {
  ReplayOge,
  ReplayOlusturmaGirdi,
  ReplayOturumDetay,
  ReplayOturumOzet,
} from '../types/replay'
import type { SayfalanmisYanit } from '../types/tahminler'

export async function replayOturumlariniGetir(params: {
  durum?: string
  makine_id?: number
  sayfa?: number
  sayfa_boyutu?: number
} = {}): Promise<SayfalanmisYanit<ReplayOturumOzet>> {
  const query = new URLSearchParams()
  if (params.durum) query.set('durum', params.durum)
  if (params.makine_id) query.set('makine_id', String(params.makine_id))
  if (params.sayfa) query.set('sayfa', String(params.sayfa))
  if (params.sayfa_boyutu) query.set('sayfa_boyutu', String(params.sayfa_boyutu))

  const qs = query.toString()
  const res = await kimlikliIstek(`/api/tahminler/replay-oturumlari/${qs ? `?${qs}` : ''}`)
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  return res.json() as Promise<SayfalanmisYanit<ReplayOturumOzet>>
}

export async function replayOturumuOlustur(girdi: ReplayOlusturmaGirdi): Promise<ReplayOturumDetay> {
  const res = await kimlikliIstek('/api/tahminler/replay-oturumlari/', {
    method: 'POST',
    body: JSON.stringify(girdi),
  })
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  return res.json() as Promise<ReplayOturumDetay>
}

export async function replayOturumuDetayiGetir(id: string): Promise<ReplayOturumDetay> {
  const res = await kimlikliIstek(`/api/tahminler/replay-oturumlari/${id}/`)
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  return res.json() as Promise<ReplayOturumDetay>
}

export async function replayOgeleriniGetir(
  id: string,
  sayfa = 1,
  sayfaBoyutu = 20
): Promise<SayfalanmisYanit<ReplayOge>> {
  const res = await kimlikliIstek(
    `/api/tahminler/replay-oturumlari/${id}/ogeler/?sayfa=${sayfa}&sayfa_boyutu=${sayfaBoyutu}`
  )
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  return res.json() as Promise<SayfalanmisYanit<ReplayOge>>
}

export async function replayBaslat(id: string, version: number): Promise<ReplayOturumDetay> {
  const res = await kimlikliIstek(`/api/tahminler/replay-oturumlari/${id}/baslat/`, {
    method: 'POST',
    body: JSON.stringify({ beklenen_version: version }),
  })
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  return res.json() as Promise<ReplayOturumDetay>
}

export async function replayAdim(
  id: string,
  version: number,
  batchBoyutu = 5
): Promise<ReplayOturumDetay> {
  const res = await kimlikliIstek(`/api/tahminler/replay-oturumlari/${id}/adim/`, {
    method: 'POST',
    body: JSON.stringify({
      beklenen_version: version,
      batch_boyutu: batchBoyutu,
    }),
  })
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  return res.json() as Promise<ReplayOturumDetay>
}

export async function replayDuraklat(id: string, version: number): Promise<ReplayOturumDetay> {
  const res = await kimlikliIstek(`/api/tahminler/replay-oturumlari/${id}/duraklat/`, {
    method: 'POST',
    body: JSON.stringify({ beklenen_version: version }),
  })
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  return res.json() as Promise<ReplayOturumDetay>
}

export async function replayDevamEt(id: string, version: number): Promise<ReplayOturumDetay> {
  const res = await kimlikliIstek(`/api/tahminler/replay-oturumlari/${id}/devam-et/`, {
    method: 'POST',
    body: JSON.stringify({ beklenen_version: version }),
  })
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  return res.json() as Promise<ReplayOturumDetay>
}

export async function replayIptalEt(id: string, version: number, reason = 'Kullanıcı tarafından iptal edildi'): Promise<ReplayOturumDetay> {
  const res = await kimlikliIstek(`/api/tahminler/replay-oturumlari/${id}/iptal/`, {
    method: 'POST',
    body: JSON.stringify({ beklenen_version: version, iptal_nedeni: reason }),
  })
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  return res.json() as Promise<ReplayOturumDetay>
}

export async function replayRetry(id: string, version: number): Promise<ReplayOturumDetay> {
  const res = await kimlikliIstek(`/api/tahminler/replay-oturumlari/${id}/basarisizlari-yeniden-dene/`, {
    method: 'POST',
    body: JSON.stringify({ beklenen_version: version }),
  })
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  return res.json() as Promise<ReplayOturumDetay>
}
