import { kimlikliIstek } from './auth'
import { responseHatasiniNormalizeEt } from '../types/apiHata'
import type {
  IsEmriAtamaGirdi,
  IsEmriDetay,
  IsEmriDurumGecisiGirdi,
  IsEmriFiltre,
  IsEmriOlusturmaGirdi,
  IsEmriOncelikOverrideGirdi,
  IsEmriOzet,
} from '../types/isEmirleri'
import type { SayfalanmisYanit } from '../types/tahminler'

export async function isEmirleriniGetir(
  params: IsEmriFiltre = {}
): Promise<SayfalanmisYanit<IsEmriOzet>> {
  const query = new URLSearchParams()
  if (params.durum) query.set('durum', params.durum)
  if (params.etkin_oncelik_seviyesi) query.set('etkin_oncelik_seviyesi', params.etkin_oncelik_seviyesi)
  if (params.genel_oncelik) query.set('genel_oncelik', String(params.genel_oncelik))
  if (params.makine_id) query.set('makine_id', String(params.makine_id))
  if (params.atanan_kullanici_id) query.set('atanan_kullanici_id', String(params.atanan_kullanici_id))
  if (params.gecikmis !== undefined) query.set('gecikmis', String(params.gecikmis))
  if (params.is_emri_numarasi) query.set('is_emri_numarasi', params.is_emri_numarasi)
  if (params.sirala) query.set('sirala', params.sirala)
  if (params.sayfa) query.set('sayfa', String(params.sayfa))
  if (params.sayfa_boyutu) query.set('sayfa_boyutu', String(params.sayfa_boyutu))

  const qs = query.toString()
  const endpoint = `/api/bakim/is-emirleri/${qs ? `?${qs}` : ''}`
  const res = await kimlikliIstek(endpoint)
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  return res.json() as Promise<SayfalanmisYanit<IsEmriOzet>>
}

export async function isEmriDetayiGetir(id: string): Promise<IsEmriDetay> {
  const res = await kimlikliIstek(`/api/bakim/is-emirleri/${id}/`)
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  return res.json() as Promise<IsEmriDetay>
}

export async function isEmriOlustur(girdi: IsEmriOlusturmaGirdi): Promise<IsEmriDetay> {
  const res = await kimlikliIstek('/api/bakim/is-emirleri/', {
    method: 'POST',
    body: JSON.stringify(girdi),
  })
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  return res.json() as Promise<IsEmriDetay>
}

export async function isEmriAta(id: string, girdi: IsEmriAtamaGirdi): Promise<IsEmriDetay> {
  const payload: Record<string, unknown> = {
    atanan_kullanici_id: girdi.atanan_kullanici_id,
    beklenen_version: girdi.beklenen_version,
  }
  if (girdi.not) {
    payload.not = girdi.not
  }

  const res = await kimlikliIstek(`/api/bakim/is-emirleri/${id}/ata/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  return res.json() as Promise<IsEmriDetay>
}

export async function isEmriDurumGecisi(
  id: string,
  girdi: IsEmriDurumGecisiGirdi
): Promise<IsEmriDetay> {
  const res = await kimlikliIstek(`/api/bakim/is-emirleri/${id}/durum-gecisi/`, {
    method: 'POST',
    body: JSON.stringify(girdi),
  })
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  return res.json() as Promise<IsEmriDetay>
}

export async function isEmriOncelikOverride(
  id: string,
  girdi: IsEmriOncelikOverrideGirdi
): Promise<IsEmriDetay> {
  const res = await kimlikliIstek(`/api/bakim/is-emirleri/${id}/oncelik-override/`, {
    method: 'POST',
    body: JSON.stringify(girdi),
  })
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  return res.json() as Promise<IsEmriDetay>
}
