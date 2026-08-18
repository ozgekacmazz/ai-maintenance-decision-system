import { kimlikliIstek } from './auth'
import { responseHatasiniNormalizeEt } from '../types/apiHata'
import type {
  RiskTahminiGirdi,
  RiskTahminiYaniti,
  SayfalanmisYanit,
  TahminKaydiOzet,
} from '../types/tahminler'

export async function hizliRiskTahmini(girdi: RiskTahminiGirdi): Promise<RiskTahminiYaniti> {
  const response = await kimlikliIstek('/api/tahminler/risk/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(girdi),
  })

  if (!response.ok) {
    throw await responseHatasiniNormalizeEt(response)
  }

  return response.json() as Promise<RiskTahminiYaniti>
}

export async function tahminKayitlariniGetir(
  parametreler: Record<string, string | number | boolean | undefined> = {}
): Promise<SayfalanmisYanit<TahminKaydiOzet>> {
  const query = new URLSearchParams()
  for (const [anahtar, deger] of Object.entries(parametreler)) {
    if (deger !== undefined && deger !== '') {
      query.set(anahtar, String(deger))
    }
  }

  const queryString = query.toString()
  const path = `/api/tahminler/kayitlar/${queryString ? `?${queryString}` : ''}`

  const response = await kimlikliIstek(path)

  if (!response.ok) {
    throw await responseHatasiniNormalizeEt(response)
  }

  return response.json() as Promise<SayfalanmisYanit<TahminKaydiOzet>>
}
