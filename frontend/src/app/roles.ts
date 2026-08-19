import type { KullaniciOzeti } from '../types/auth'

export function adminMi(kullanici: Pick<KullaniciOzeti, 'rol'> | null | undefined): boolean {
  return kullanici?.rol === 'ADMIN'
}
