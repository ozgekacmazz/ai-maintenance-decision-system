export interface RiskTahminiGirdi {
  urun_tipi: 'L' | 'M' | 'H'
  hava_sicakligi_k: number
  proses_sicakligi_k: number
  donus_hizi_rpm: number
  tork_nm: number
  takim_asinmasi_dk: number
}

export interface GuvenilirAday {
  kod: string
  olasilik: number
  threshold: number
}

export interface DeneyselSinyal {
  kod: string
  olasilik: number
  threshold: number
  esik_asildi: boolean
  guven_durumu: string
  operasyonel_kullanima_uygun: boolean
}

export interface ArizaTipiDegerlendirmesi {
  durum: 'RISK_ESIK_ALTINDA' | 'DEGERLENDIRILDI' | string
  model_version?: string
  pipeline_version?: string
  guvenilir_adaylar: GuvenilirAday[]
  deneysel_sinyaller: DeneyselSinyal[]
  belirsiz_fiziksel_tip: boolean
}

export interface ShapEtkisi {
  feature: string
  gorunen_ad: string
  original_feature_value: number | boolean
  model_feature_value: number
  birim: string | null
  shap_value: number
  yon: 'RISKI_ARTIRIR' | 'RISKI_AZALTIR' | 'NOTR' | string
}

export interface RiskAciklamasi {
  target: string
  output_space: string
  base_value: number
  ilk_etkiler: ShapEtkisi[]
}

export interface AciklanabilirlikInfo {
  durum: 'RISK_ESIK_ALTINDA' | 'ACIKLANDI' | string
  risk_aciklamasi?: RiskAciklamasi | null
}

export interface RiskTahminiYaniti {
  risk_orani: number
  risk_uyarisi: boolean
  threshold: number
  model_version: string
  pipeline_version: string
  ariza_tipi_degerlendirmesi: ArizaTipiDegerlendirmesi
  aciklanabilirlik?: AciklanabilirlikInfo
}

export interface TahminKaydiOzet {
  id: string
  makine: {
    id: number
    kod: string
    ad: string
  }
  olcum_zamani: string
  risk_orani: number
  risk_uyarisi: boolean
  en_yuksek_guvenilir_ariza_tipi: string | null
  belirsiz_fiziksel_tip: boolean
  kaynak: string
  olusturan: {
    id: number
    kullanici_adi: string
  }
  trace_id: string
  erp_snapshot_var: boolean
  nihai_oncelik_skoru: number | null
  oncelik_seviyesi: 'KRITIK' | 'YUKSEK' | 'ORTA' | 'DUSUK' | null
  ana_aksiyon:
    | 'ACIL_TEKNIK_DEGERLENDIRME'
    | 'ONCELIKLI_BAKIM_PLANLA'
    | 'PLANLI_KONTROL'
    | 'IZLEMEYE_DEVAM'
    | 'TEKNIK_INCELEME'
    | null
  karar_guveni: 'YUKSEK' | 'ORTA' | 'DUSUK' | null
}

export interface SayfalanmisYanit<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export function arizaTipiMetni(kod: string | null | undefined): string {
  if (!kod) return 'Belirlenemedi'
  switch (kod) {
    case 'HDF':
      return 'Isı dağılımı sorunu'
    case 'PWF':
      return 'Güç kaynaklı sorun'
    case 'OSF':
      return 'Aşırı zorlanma'
    case 'TWF':
      return 'Takım aşınması sinyali'
    case 'RNF':
      return 'Rastgele gürültü'
    default:
      return kod
  }
}

export function oncelikSeviyesiMetni(seviye: string | null | undefined): string {
  if (!seviye) return 'Belirtilmedi'
  switch (seviye) {
    case 'KRITIK':
      return 'Kritik'
    case 'YUKSEK':
      return 'Yüksek'
    case 'ORTA':
      return 'Orta'
    case 'DUSUK':
      return 'Düşük'
    default:
      return seviye
  }
}

export function anaAksiyonMetni(aksiyon: string | null | undefined): string {
  if (!aksiyon) return 'Planlı izleme'
  switch (aksiyon) {
    case 'ACIL_TEKNIK_DEGERLENDIRME':
      return 'Acil teknik değerlendirme'
    case 'ONCELIKLI_BAKIM_PLANLA':
      return 'Öncelikli bakım planla'
    case 'PLANLI_KONTROL':
      return 'Planlı kontrol'
    case 'IZLEMEYE_DEVAM':
      return 'İzlemeye devam'
    case 'TEKNIK_INCELEME':
      return 'Teknik inceleme'
    default:
      return aksiyon
  }
}

export function yonMetni(yon: string): string {
  switch (yon) {
    case 'RISKI_ARTIRIR':
      return 'Riski artırıyor'
    case 'RISKI_AZALTIR':
      return 'Riski azaltıyor'
    case 'NOTR':
      return 'Belirgin etkisi yok'
    default:
      return yon
  }
}

export function rolMetni(rol: string | undefined): string {
  if (rol === 'ADMIN') return 'Yönetici'
  if (rol === 'USER') return 'Kullanıcı'
  return rol || 'Kullanıcı'
}
