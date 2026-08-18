export type KullaniciRolu = 'USER' | 'ADMIN'

export interface KullaniciOzeti {
  id: number
  username: string
  email?: string
  rol: KullaniciRolu
}

export interface GirisYaniti {
  access: string
  kullanici: KullaniciOzeti
}
