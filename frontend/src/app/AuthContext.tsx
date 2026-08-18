import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

import { accessTokeniYenile, cikisYap, girisYap, kullaniciyiGetir } from '../api/auth'
import type { KullaniciOzeti } from '../types/auth'

interface AuthDegeri {
  kullanici: KullaniciOzeti | null
  yukleniyor: boolean
  giris: (username: string, password: string) => Promise<void>
  cikis: () => Promise<void>
}

const AuthContext = createContext<AuthDegeri | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [kullanici, setKullanici] = useState<KullaniciOzeti | null>(null)
  const [yukleniyor, setYukleniyor] = useState(true)

  useEffect(() => {
    let aktif = true
    accessTokeniYenile()
      .then(kullaniciyiGetir)
      .then((bilgi) => { if (aktif) setKullanici(bilgi) })
      .catch(() => { if (aktif) setKullanici(null) })
      .finally(() => { if (aktif) setYukleniyor(false) })
    return () => { aktif = false }
  }, [])

  async function giris(username: string, password: string) {
    const yanit = await girisYap(username, password)
    setKullanici(yanit.kullanici)
  }

  async function cikis() {
    await cikisYap()
    setKullanici(null)
  }

  return <AuthContext.Provider value={{ kullanici, yukleniyor, giris, cikis }}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth, AuthProvider içinde kullanılmalıdır.')
  return context
}
