export interface Makine {
  id: number
  makine_kodu: string
  ad: string
  kritiklik_seviyesi: number
  aktif: boolean
  olusturulma_zamani: string
  guncellenme_zamani: string
}

export interface MakineYazmaGirdi {
  makine_kodu: string
  ad: string
  kritiklik_seviyesi: number
  aktif?: boolean
}

export interface Parca {
  id: number
  parca_kodu: string
  ad: string
  aktif: boolean
  olusturulma_zamani: string
  guncellenme_zamani: string
}

export interface ParcaYazmaGirdi {
  parca_kodu: string
  ad: string
  aktif?: boolean
}

export interface StokItem {
  id: number
  parca: Parca
  toplam_stok: number
  minimum_stok: number
  tedarik_gun: number
  kullanilabilir_stok: number
  stok_durumu: 'MEVCUT' | 'KRITIK' | 'TUKENDI' | 'KAYIT_YOK'
  stok_yeterli: boolean
  guncellenme_zamani: string
}

export interface StokGuncelleGirdi {
  toplam_stok?: number
  minimum_stok?: number
  tedarik_gun?: number
}

export interface KullaniciYonetimItem {
  id: number
  username: string
  email: string
  rol: 'ADMIN' | 'USER'
  is_active: boolean
  date_joined: string
}

export interface KullaniciOlusturGirdi {
  username: string
  email?: string
  password: string
  rol: 'ADMIN' | 'USER'
  is_active?: boolean
}
