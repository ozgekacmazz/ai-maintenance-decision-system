import { kimlikliIstek } from './auth'
import { responseHatasiniNormalizeEt } from '../types/apiHata'
import type {
  RiskTahminiGirdi,
  InputDomainContract,
  RiskTahminiYaniti,
  SayfalanmisYanit,
  TahminKaydiDetay,
  TahminKaydiListeParametreleri,
  TahminKaydiOzet,
  TahminKaydiYazmaGirdi,
  TahminLoglariParametreleri,
  TahminLogu,
} from '../types/tahminler'

export async function inputDomainContractGetir(): Promise<InputDomainContract> {
  const response = await kimlikliIstek('/api/tahminler/input-domain/')
  if (!response.ok) throw await responseHatasiniNormalizeEt(response)
  return response.json() as Promise<InputDomainContract>
}

export async function tahminLoglariniGetir(
  parametreler: TahminLoglariParametreleri = {}
): Promise<SayfalanmisYanit<TahminLogu>> {
  const query = new URLSearchParams()
  for (const [anahtar, deger] of Object.entries(parametreler)) {
    if (deger !== undefined && deger !== '') query.set(anahtar, String(deger))
  }
  const queryString = query.toString()
  const response = await kimlikliIstek(`/api/tahminler/loglari/${queryString ? `?${queryString}` : ''}`)
  if (!response.ok) throw await responseHatasiniNormalizeEt(response)
  return response.json() as Promise<SayfalanmisYanit<TahminLogu>>
}

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
  parametreler: TahminKaydiListeParametreleri = {}
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

export async function tahminKaydiDetayiGetir(id: string): Promise<TahminKaydiDetay> {
  const response = await kimlikliIstek(`/api/tahminler/kayitlar/${id}/`)

  if (!response.ok) {
    throw await responseHatasiniNormalizeEt(response)
  }

  return response.json() as Promise<TahminKaydiDetay>
}

export async function tahminReddet(id: string, redNedeni: string): Promise<TahminKaydiDetay> {
  const response = await kimlikliIstek(`/api/tahminler/kayitlar/${id}/reddet/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ red_nedeni: redNedeni }),
  })

  if (!response.ok) {
    throw await responseHatasiniNormalizeEt(response)
  }

  return response.json() as Promise<TahminKaydiDetay>
}

export async function kaliciTahminKaydiOlustur(
  veriler: TahminKaydiYazmaGirdi
): Promise<TahminKaydiDetay> {
  const response = await kimlikliIstek('/api/tahminler/kayitlar/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(veriler),
  })

  if (!response.ok) {
    throw await responseHatasiniNormalizeEt(response)
  }

  return response.json() as Promise<TahminKaydiDetay>
}
