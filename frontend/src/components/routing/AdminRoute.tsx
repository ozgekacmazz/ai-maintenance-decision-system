import { Outlet } from 'react-router-dom'
import { useAuth } from '../../app/AuthContext'
import { YetkisizErisim } from './YetkisizErisim'
import { adminMi } from '../../app/roles'

export function AdminRoute() {
  const { kullanici, yukleniyor } = useAuth()

  if (yukleniyor) {
    return <p role="status">Oturum yükleniyor…</p>
  }

  if (!adminMi(kullanici)) {
    return <YetkisizErisim />
  }

  return <Outlet />
}
