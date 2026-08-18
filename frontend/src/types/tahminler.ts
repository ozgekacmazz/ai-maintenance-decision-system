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

export interface MakineOzet {
  id: number
  kod: string
  ad: string
  tip?: string
  kritiklik?: number
  aktif?: boolean
}

export interface TahminKaydiYazmaGirdi {
  makine_id: number
  olcum_zamani: string
  kaynak: 'MANUEL' | 'REPLAY' | 'ENTEGRASYON' | string
  idempotency_key: string
  sensor_verisi: RiskTahminiGirdi
}

export interface ErpSnapshotItem {
  id: number
  ariza_tipi: string
  parca_kodu_snapshot: string
  parca_adi_snapshot: string
  gerekli_miktar: number
  stok_durumu: 'MEVCUT' | 'KAYIT_YOK' | string
  toplam_stok: number | null
  kullanilabilir_stok: number | null
  minimum_stok: number | null
  tedarik_gun: number | null
  stok_yeterli: boolean
  deneysel: boolean
  onerilen_aksiyon_snapshot: string
}

export interface KararGerekcesi {
  kod: string
  mesaj: string
  etki: string
  puan_etkisi: number | null
}

export interface KararUyarisi {
  kod: string
  mesaj: string
}

export interface BakimKarariSnapshotInfo {
  motor_surumu: string
  teknik_aciliyet_skoru: number
  tedarik_riski_skoru: number
  nihai_oncelik_skoru: number
  oncelik_seviyesi: 'KRITIK' | 'YUKSEK' | 'ORTA' | 'DUSUK' | string
  ana_aksiyon: string
  destekleyici_aksiyonlar: string[]
  ana_ariza_tipi: string | null
  karar_guveni: 'YUKSEK' | 'ORTA' | 'DUSUK' | string
  gerekceler: KararGerekcesi[]
  uyarilar: KararUyarisi[]
  olusturulma_zamani: string
}

export interface ArizaTipiItem {
  id: number
  kod: string
  olasilik: number
  threshold: number
  esik_asildi: boolean
  guvenilir: boolean
  deneysel: boolean
  guven_durumu: string
  operasyonel_kullanima_uygun: boolean
  siralama: number
  shap_etkileri: ShapEtkisi[]
}

export interface TahminKaydiDetay {
  id: string
  tekrarlandi?: boolean
  makine: {
    id: number
    kod: string
    ad: string
    kritiklik_snapshot: number
  }
  olcum_zamani: string
  olusturulma_zamani: string
  kaynak: string
  sensor_snapshot: RiskTahminiGirdi
  tahmin: {
    risk_orani: number
    risk_uyarisi: boolean
    threshold: number
    model_version: string
    pipeline_version: string
    base_value: number | null
  }
  failure_type_durum: string
  failure_type_model_version: string | null
  failure_type_pipeline_version: string | null
  belirsiz_fiziksel_tip: boolean
  aciklanabilirlik_durum: string
  ariza_tipleri: ArizaTipiItem[]
  shap_etkileri: ShapEtkisi[]
  erp_snapshotlari: ErpSnapshotItem[]
  olusturan: {
    id: number
    kullanici_adi: string
  }
  trace_id: string
  bakim_karari: BakimKarariSnapshotInfo | null
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

export function kaynakMetni(kaynak: string | null | undefined): string {
  if (!kaynak) return 'Belirtilmedi'
  switch (kaynak) {
    case 'MANUEL':
      return 'Manuel değerlendirme'
    case 'REPLAY':
      return 'Replay'
    case 'ENTEGRASYON':
      return 'Entegrasyon'
    default:
      return kaynak
  }
}

export function kararGuveniMetni(guven: string | null | undefined): string {
  if (!guven) return 'Belirtilmedi'
  switch (guven) {
    case 'YUKSEK':
      return 'Yüksek'
    case 'ORTA':
      return 'Orta'
    case 'DUSUK':
      return 'Düşük'
    default:
      return guven
  }
}

export function destekleyiciAksiyonMetni(aksiyon: string): string {
  switch (aksiyon) {
    case 'STOK_VERISINI_DOGRULA':
      return 'Stok bilgisini doğrula'
    case 'TEDARIK_SURECINI_BASLAT':
      return 'Tedarik sürecini başlat'
    case 'BAKIM_EKIBINI_BILGILENDIR':
      return 'Bakım ekibini bilgilendir'
    default:
      return aksiyon
  }
}

export function urunTipiMetni(tip: string | null | undefined): string {
  if (!tip) return 'Belirtilmedi'
  switch (tip) {
    case 'L':
      return 'Düşük Kalite (L)'
    case 'M':
      return 'Orta Kalite (M)'
    case 'H':
      return 'Yüksek Kalite (H)'
    default:
      return tip
  }
}

export function sayiFormatla(val: unknown, decimals: number = 2): string {
  if (val === null || val === undefined || val === '') return '-'
  const num = typeof val === 'number' ? val : parseFloat(String(val))
  if (Number.isNaN(num)) return String(val)
  return num.toLocaleString('tr-TR', {
    maximumFractionDigits: decimals,
  })
}
