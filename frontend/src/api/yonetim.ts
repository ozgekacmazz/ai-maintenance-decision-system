import { kimlikliIstek } from './auth'
import { responseHatasiniNormalizeEt } from '../types/apiHata'
import type { Makine, Parca, StokItem, KullaniciYonetimItem, KullaniciOlusturGirdi } from '../types/yonetim'
import type { SayfalanmisYanit } from '../types/tahminler'

interface MakineApiItem {
  id: number
  kod?: string
  makine_kodu?: string
  ad: string
  kritiklik?: number
  kritiklik_seviyesi?: number
  aktif: boolean
  olusturulma_zamani: string
  guncellenme_zamani: string
}

interface ParcaApiItem {
  id: number
  kod?: string
  parca_kodu?: string
  ad: string
  aktif: boolean
  olusturulma_zamani: string
  guncellenme_zamani: string
}

interface StokApiItem {
  id: number
  parca_id: number
  parca_kodu: string
  parca_adi: string
  stok_adedi: number
  tedarik_suresi_gun: number
  kritik_stok_seviyesi: number
  olusturulma_zamani: string
  guncellenme_zamani: string
}

export async function makineleriGetirFull(
  sayfa = 1,
  sayfaBoyutu = 10
): Promise<SayfalanmisYanit<Makine>> {
  const res = await kimlikliIstek(
    `/api/makineler/?sayfa=${sayfa}&sayfa_boyutu=${sayfaBoyutu}`
  )
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  const data = (await res.json()) as SayfalanmisYanit<MakineApiItem>
  return {
    ...data,
    results: (data.results || []).map((item) => ({
      id: item.id,
      makine_kodu: item.kod || item.makine_kodu || '',
      ad: item.ad,
      kritiklik_seviyesi: item.kritiklik ?? item.kritiklik_seviyesi ?? 3,
      aktif: item.aktif,
      olusturulma_zamani: item.olusturulma_zamani,
      guncellenme_zamani: item.guncellenme_zamani,
    })),
  }
}

export async function makineOlustur(girdi: {
  makine_kodu: string
  ad: string
  kritiklik_seviyesi: number
}): Promise<Makine> {
  const res = await kimlikliIstek('/api/makineler/', {
    method: 'POST',
    body: JSON.stringify({
      kod: girdi.makine_kodu,
      ad: girdi.ad,
      tip: 'Standart',
      kritiklik: girdi.kritiklik_seviyesi,
      aktif: true,
    }),
  })
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  const item = (await res.json()) as MakineApiItem
  return {
    id: item.id,
    makine_kodu: item.kod || item.makine_kodu || '',
    ad: item.ad,
    kritiklik_seviyesi: item.kritiklik ?? item.kritiklik_seviyesi ?? 3,
    aktif: item.aktif,
    olusturulma_zamani: item.olusturulma_zamani,
    guncellenme_zamani: item.guncellenme_zamani,
  }
}

export async function makineGuncelle(
  id: number,
  girdi: { makine_kodu?: string; ad?: string; kritiklik_seviyesi?: number }
): Promise<Makine> {
  const body: Record<string, unknown> = {}
  if (girdi.makine_kodu) body.kod = girdi.makine_kodu
  if (girdi.ad) body.ad = girdi.ad
  if (girdi.kritiklik_seviyesi !== undefined) body.kritiklik = girdi.kritiklik_seviyesi

  const res = await kimlikliIstek(`/api/makineler/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  const item = (await res.json()) as MakineApiItem
  return {
    id: item.id,
    makine_kodu: item.kod || item.makine_kodu || '',
    ad: item.ad,
    kritiklik_seviyesi: item.kritiklik ?? item.kritiklik_seviyesi ?? 3,
    aktif: item.aktif,
    olusturulma_zamani: item.olusturulma_zamani,
    guncellenme_zamani: item.guncellenme_zamani,
  }
}

export async function makineAktiflikDegistir(id: number, aktif: boolean): Promise<Makine> {
  const res = await kimlikliIstek(`/api/makineler/${id}/aktiflik/`, {
    method: 'POST',
    body: JSON.stringify({ aktif }),
  })
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  const item = (await res.json()) as MakineApiItem
  return {
    id: item.id,
    makine_kodu: item.kod || item.makine_kodu || '',
    ad: item.ad,
    kritiklik_seviyesi: item.kritiklik ?? item.kritiklik_seviyesi ?? 3,
    aktif: item.aktif,
    olusturulma_zamani: item.olusturulma_zamani,
    guncellenme_zamani: item.guncellenme_zamani,
  }
}

export async function parcalariGetir(
  sayfa = 1,
  sayfaBoyutu = 10
): Promise<SayfalanmisYanit<Parca>> {
  const res = await kimlikliIstek(`/api/parcalar/?sayfa=${sayfa}&sayfa_boyutu=${sayfaBoyutu}`)
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  const data = (await res.json()) as SayfalanmisYanit<ParcaApiItem>
  return {
    ...data,
    results: (data.results || []).map((item) => ({
      id: item.id,
      parca_kodu: item.kod || item.parca_kodu || '',
      ad: item.ad,
      aktif: item.aktif,
      olusturulma_zamani: item.olusturulma_zamani,
      guncellenme_zamani: item.guncellenme_zamani,
    })),
  }
}

export async function parcaOlustur(girdi: { parca_kodu: string; ad: string }): Promise<Parca> {
  const res = await kimlikliIstek('/api/parcalar/', {
    method: 'POST',
    body: JSON.stringify({
      kod: girdi.parca_kodu,
      ad: girdi.ad,
      aktif: true,
    }),
  })
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  const item = (await res.json()) as ParcaApiItem
  return {
    id: item.id,
    parca_kodu: item.kod || item.parca_kodu || '',
    ad: item.ad,
    aktif: item.aktif,
    olusturulma_zamani: item.olusturulma_zamani,
    guncellenme_zamani: item.guncellenme_zamani,
  }
}

export async function parcaGuncelle(
  id: number,
  girdi: { parca_kodu?: string; ad?: string }
): Promise<Parca> {
  const body: Record<string, unknown> = {}
  if (girdi.parca_kodu) body.kod = girdi.parca_kodu
  if (girdi.ad) body.ad = girdi.ad

  const res = await kimlikliIstek(`/api/parcalar/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  const item = (await res.json()) as ParcaApiItem
  return {
    id: item.id,
    parca_kodu: item.kod || item.parca_kodu || '',
    ad: item.ad,
    aktif: item.aktif,
    olusturulma_zamani: item.olusturulma_zamani,
    guncellenme_zamani: item.guncellenme_zamani,
  }
}

export async function parcaAktiflikDegistir(id: number, aktif: boolean): Promise<Parca> {
  const res = await kimlikliIstek(`/api/parcalar/${id}/aktiflik/`, {
    method: 'POST',
    body: JSON.stringify({ aktif }),
  })
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  const item = (await res.json()) as ParcaApiItem
  return {
    id: item.id,
    parca_kodu: item.kod || item.parca_kodu || '',
    ad: item.ad,
    aktif: item.aktif,
    olusturulma_zamani: item.olusturulma_zamani,
    guncellenme_zamani: item.guncellenme_zamani,
  }
}

export async function stoklariGetir(
  sayfa = 1,
  sayfaBoyutu = 10
): Promise<SayfalanmisYanit<StokItem>> {
  const res = await kimlikliIstek(`/api/stoklar/?sayfa=${sayfa}&sayfa_boyutu=${sayfaBoyutu}`)
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  const data = (await res.json()) as SayfalanmisYanit<StokApiItem>
  return {
    ...data,
    results: (data.results || []).map((item) => ({
      id: item.id,
      parca: {
        id: item.parca_id,
        parca_kodu: item.parca_kodu,
        ad: item.parca_adi,
        aktif: true,
        olusturulma_zamani: item.olusturulma_zamani,
        guncellenme_zamani: item.guncellenme_zamani,
      },
      toplam_stok: item.stok_adedi,
      minimum_stok: item.kritik_stok_seviyesi,
      tedarik_gun: item.tedarik_suresi_gun,
      kullanilabilir_stok: item.stok_adedi,
      stok_durumu:
        item.stok_adedi === 0
          ? 'TUKENDI'
          : item.stok_adedi <= item.kritik_stok_seviyesi
          ? 'KRITIK'
          : 'MEVCUT',
      stok_yeterli: item.stok_adedi > item.kritik_stok_seviyesi,
      guncellenme_zamani: item.guncellenme_zamani,
    })),
  }
}

export async function stokGuncelle(
  id: number,
  girdi: { toplam_stok?: number; minimum_stok?: number; tedarik_gun?: number }
): Promise<StokItem> {
  const body: Record<string, unknown> = {}
  if (girdi.toplam_stok !== undefined) body.stok_adedi = girdi.toplam_stok
  if (girdi.minimum_stok !== undefined) body.kritik_stok_seviyesi = girdi.minimum_stok
  if (girdi.tedarik_gun !== undefined) body.tedarik_suresi_gun = girdi.tedarik_gun

  const res = await kimlikliIstek(`/api/stoklar/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  const item = (await res.json()) as StokApiItem
  return {
    id: item.id,
    parca: {
      id: item.parca_id,
      parca_kodu: item.parca_kodu,
      ad: item.parca_adi,
      aktif: true,
      olusturulma_zamani: item.olusturulma_zamani,
      guncellenme_zamani: item.guncellenme_zamani,
    },
    toplam_stok: item.stok_adedi,
    minimum_stok: item.kritik_stok_seviyesi,
    tedarik_gun: item.tedarik_suresi_gun,
    kullanilabilir_stok: item.stok_adedi,
    stok_durumu:
      item.stok_adedi === 0
        ? 'TUKENDI'
        : item.stok_adedi <= item.kritik_stok_seviyesi
        ? 'KRITIK'
        : 'MEVCUT',
    stok_yeterli: item.stok_adedi > item.kritik_stok_seviyesi,
    guncellenme_zamani: item.guncellenme_zamani,
  }
}

export async function adminKontrolEt(): Promise<{ durum: string; rol: string }> {
  const res = await kimlikliIstek('/api/auth/admin-kontrol/')
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  return res.json() as Promise<{ durum: string; rol: string }>
}

export async function kullanicilariGetir(): Promise<KullaniciYonetimItem[]> {
  const res = await kimlikliIstek('/api/auth/kullanicilar/')
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  return res.json() as Promise<KullaniciYonetimItem[]>
}

export async function kullaniciOlustur(girdi: KullaniciOlusturGirdi): Promise<KullaniciYonetimItem> {
  const res = await kimlikliIstek('/api/auth/kullanicilar/', {
    method: 'POST',
    body: JSON.stringify(girdi),
  })
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  return res.json() as Promise<KullaniciYonetimItem>
}

export async function kullaniciGuncelle(
  id: number,
  girdi: { is_active?: boolean; rol?: 'ADMIN' | 'USER'; email?: string }
): Promise<KullaniciYonetimItem> {
  const res = await kimlikliIstek(`/api/auth/kullanicilar/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(girdi),
  })
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  return res.json() as Promise<KullaniciYonetimItem>
}

export async function kullaniciSifreSifirla(
  id: number,
  yeniSifre: string
): Promise<{ mesaj: string }> {
  const res = await kimlikliIstek(`/api/auth/kullanicilar/${id}/sifre-sifirla/`, {
    method: 'POST',
    body: JSON.stringify({ yeni_sifre: yeniSifre }),
  })
  if (!res.ok) throw await responseHatasiniNormalizeEt(res)
  return res.json() as Promise<{ mesaj: string }>
}
