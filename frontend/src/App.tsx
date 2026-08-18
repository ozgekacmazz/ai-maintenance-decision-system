import { AltyapiKontrol } from './pages/AltyapiKontrol'
import { AuthProvider, useAuth } from './app/AuthContext'
import { Login } from './pages/Login'
import './app/styles.css'

export default function App() {
  return <AuthProvider><KorumaliUygulama /></AuthProvider>
}

function KorumaliUygulama() {
  const { kullanici, yukleniyor } = useAuth()
  if (yukleniyor) return <main className="sayfa"><p role="status">Oturum yükleniyor…</p></main>
  return kullanici ? <AltyapiKontrol /> : <Login />
}
