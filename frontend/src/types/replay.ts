import type { MakineOzeti } from './isEmirleri'

export type ReplayDurum =
  | 'HAZIR'
  | 'CALISIYOR'
  | 'DURAKLATILDI'
  | 'TAMAMLANDI'
  | 'HATALI'
  | 'IPTAL_EDILDI'

export type ReplayOgeDurum = 'BEKLIYOR' | 'ISLENIYOR' | 'BASARILI' | 'BASARISIZ' | 'ATLANDI'

export interface ReplayIlerleme {
  bekleyen: number
  isleniyor: number
  basarili: number
  basarisiz: number
  atlandi: number
  tamamlanma_yuzdesi: number
}

export interface ReplayLabelMetrics {
  precision: number
  recall: number
  f1: number
  pr_auc: number | null
  support: number
  predicted_positive: number
  confusion_matrix: ReplayConfusionMatrix
}

export interface ReplayConfusionMatrix {
  true_negative: number
  false_positive: number
  false_negative: number
  true_positive: number
}

export interface ReplayFailureTypeMetrics {
  tn: number
  fp: number
  fn: number
  tp: number
  precision: number
  recall: number
  f1: number
  support: number
  predicted_positive: number
  politika: string
}

export interface ReplayMetrikler {
  degerlendirilen_oge_sayisi: number
  binary: ReplayLabelMetrics | null
  failure_types: Record<string, ReplayFailureTypeMetrics>
  rnf_ground_truth_count: number
  metrik_uyarilari: string[]
}

export interface ReplayOlay {
  olay_tipi: string
  onceki_durum: ReplayDurum | null
  yeni_durum: ReplayDurum | null
  version: number
  olusturulma_zamani: string
}

export interface ReplayOge {
  id: number
  sira: number
  external_machine_id: string
  durum: ReplayOgeDurum
  tahmin_kaydi_id: string | null
  hata_mesaji: string | null
  islenme_zamani: string | null
  risk_uyarisi: boolean | null
  oncelik_seviyesi: string | null
}

export interface ReplayOturumOzet {
  id: string
  makine: MakineOzeti
  split: 'test' | 'validation' | 'all'
  durum: ReplayDurum
  baslangic_ofseti: number
  toplam_oge: number
  varsayilan_batch_boyutu: number
  sanal_aralik_saniye: number
  baslatilma_zamani: string | null
  tamamlanma_zamani: string | null
  iptal_zamani: string | null
  hata_mesaji: string | null
  ilerleme: ReplayIlerleme
  olusturulma_zamani: string
  version: number
}

export interface ReplayOturumDetay extends ReplayOturumOzet {
  metrikler: ReplayMetrikler
  olaylar: ReplayOlay[]
  son_ogeler: ReplayOge[]
}

export interface ReplayOlusturmaGirdi {
  makine_id: number
  split: 'test' | 'validation' | 'all'
  baslangic_ofseti?: number
  kayit_sayisi?: number
  varsayilan_batch_boyutu?: number
  sanal_aralik_saniye?: number
}

export function replayDurumMetni(durum: ReplayDurum | string | null | undefined): string {
  if (!durum) return 'Belirtilmedi'
  switch (durum) {
    case 'HAZIR':
      return 'Hazır'
    case 'CALISIYOR':
      return 'Çalışıyor'
    case 'DURAKLATILDI':
      return 'Duraklatıldı'
    case 'TAMAMLANDI':
      return 'Tamamlandı'
    case 'HATALI':
      return 'Hatalı'
    case 'IPTAL_EDILDI':
      return 'İptal Edildi'
    default:
      return durum
  }
}

export function replayOgeDurumMetni(durum: ReplayOgeDurum | string | null | undefined): string {
  if (!durum) return 'Belirtilmedi'
  switch (durum) {
    case 'BEKLIYOR':
      return 'Bekliyor'
    case 'ISLENIYOR':
      return 'İşleniyor'
    case 'BASARILI':
      return 'Başarılı'
    case 'BASARISIZ':
      return 'Başarısız'
    case 'ATLANDI':
      return 'Atlandı'
    default:
      return durum
  }
}
