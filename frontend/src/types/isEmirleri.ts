import type { KullaniciOzeti } from './tahminler'

export type IsEmriDurum =
  | 'ACIK'
  | 'ATANDI'
  | 'DEVAM_EDIYOR'
  | 'BEKLEMEDE'
  | 'TAMAMLANDI'
  | 'IPTAL_EDILDI'

export type IsEmriOncelik = 'DUSUK' | 'ORTA' | 'YUKSEK' | 'KRITIK'
export type GenelOncelik = 1 | 2 | 3 | 4 | 5

export interface MakineOzeti {
  id: number
  kod: string
  ad: string
}

export interface IsEmriOlay {
  id: number
  olay_tipi: string
  onceki_durum: IsEmriDurum | null
  yeni_durum: IsEmriDurum | null
  onceki_oncelik?: IsEmriOncelik | null
  yeni_oncelik?: IsEmriOncelik | null
  onceki_genel_oncelik: GenelOncelik | null
  yeni_genel_oncelik: GenelOncelik | null
  gerceklestiren_kullanici_adi: string
  detay: Record<string, unknown> | null
  olusturulma_zamani: string
}

export interface IsEmriErpOzeti {
  parca_kodu: string
  parca_adi: string
  stok_durumu: string
  stok_yeterli: boolean
  gerekli_miktar: number
}

export interface IsEmriKaynakKarar {
  motor_surumu: string
  teknik_aciliyet_skoru: number
  tedarik_riski_skoru: number
  nihai_oncelik_skoru: number
  oncelik_seviyesi: IsEmriOncelik
  ana_aksiyon: string
  karar_guveni: string
  ana_ariza_tipi: string
}

export interface IsEmriOzet {
  id: string
  is_emri_numarasi: string
  makine: MakineOzeti
  ana_aksiyon: string | null
  erp_ozeti: IsEmriErpOzeti[]
  durum: IsEmriDurum
  etkin_oncelik_seviyesi: IsEmriOncelik
  kaynak_oncelik_seviyesi: IsEmriOncelik
  kaynak_genel_oncelik: GenelOncelik | null
  kaynak_genel_oncelik_formul_surumu: string | null
  etkin_genel_oncelik: GenelOncelik | null
  atanan_kullanici: KullaniciOzeti | null
  hedef_mudahale_zamani: string
  gecikmis: boolean
  olcum_zamani: string
  olusturan: KullaniciOzeti
  olusturulma_zamani: string
  version: number
}

export interface IsEmriDetay extends IsEmriOzet {
  tahmin_kaydi_id: string
  baslik: string
  aciklama: string
  politika_surumu: string
  kaynak_karar: IsEmriKaynakKarar
  manuel_oncelik_override: boolean
  override_nedeni: string | null
  planlanan_baslangic_zamani: string | null
  gercek_baslangic_zamani: string | null
  tamamlanma_zamani: string | null
  iptal_zamani: string | null
  tamamlama_notu: string | null
  iptal_nedeni: string | null
  bekleme_nedeni: string | null
  erp_ozeti: IsEmriErpOzeti[]
  olaylar: IsEmriOlay[]
  guncellenme_zamani: string
  tekrarlandi: boolean
}

export interface IsEmriFiltre {
  durum?: IsEmriDurum
  etkin_oncelik_seviyesi?: IsEmriOncelik
  genel_oncelik?: GenelOncelik
  kaynak_oncelik_seviyesi?: IsEmriOncelik
  makine_id?: number
  atanan_kullanici_id?: number
  olusturan_id?: number
  gecikmis?: boolean
  manuel_oncelik_override?: boolean
  is_emri_numarasi?: string
  sirala?: string
  sayfa?: number
  sayfa_boyutu?: number
}

export interface IsEmriOlusturmaGirdi {
  tahmin_kaydi_id: string
  idempotency_key: string
  baslik: string
  aciklama: string
}

export interface IsEmriDurumGecisiGirdi {
  beklenen_version: number
  hedef_durum: IsEmriDurum
  neden?: string
  bekleme_nedeni?: string
  tamamlama_notu?: string
  iptal_nedeni?: string
}

export interface IsEmriAtamaGirdi {
  atanan_kullanici_id: number
  beklenen_version: number
  not?: string
}

export type IsEmriOncelikOverrideGirdi = {
  beklenen_version: number
  override_nedeni: string
} & (
  | { genel_oncelik: GenelOncelik; etkin_oncelik_seviyesi?: never }
  | { etkin_oncelik_seviyesi: IsEmriOncelik; genel_oncelik?: never }
)

export function isEmriDurumMetni(durum: IsEmriDurum | string | null | undefined): string {
  if (!durum) return 'Belirtilmedi'
  switch (durum) {
    case 'ACIK':
      return 'Açık'
    case 'ATANDI':
      return 'Atandı'
    case 'DEVAM_EDIYOR':
      return 'Devam Ediyor'
    case 'BEKLEMEDE':
      return 'Beklemede'
    case 'TAMAMLANDI':
      return 'Tamamlandı'
    case 'IPTAL_EDILDI':
      return 'İptal Edildi'
    default:
      return durum
  }
}

export function isEmriOncelikMetni(oncelik: IsEmriOncelik | string | null | undefined): string {
  if (!oncelik) return 'Belirtilmedi'
  switch (oncelik) {
    case 'KRITIK':
      return 'Kritik'
    case 'YUKSEK':
      return 'Yüksek'
    case 'ORTA':
      return 'Orta'
    case 'DUSUK':
      return 'Düşük'
    default:
      return oncelik
  }
}

export const GECERLI_DURUM_GECISLERI: Record<IsEmriDurum, IsEmriDurum[]> = {
  ACIK: ['IPTAL_EDILDI'],
  ATANDI: ['DEVAM_EDIYOR', 'BEKLEMEDE', 'IPTAL_EDILDI'],
  DEVAM_EDIYOR: ['BEKLEMEDE', 'TAMAMLANDI', 'IPTAL_EDILDI'],
  BEKLEMEDE: ['DEVAM_EDIYOR', 'IPTAL_EDILDI'],
  TAMAMLANDI: [],
  IPTAL_EDILDI: [],
}
