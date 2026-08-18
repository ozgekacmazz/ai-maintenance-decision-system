import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './app/AuthContext'
import { AppShell } from './components/layout/AppShell'
import { Dashboard } from './pages/Dashboard'
import { HizliAnaliz } from './pages/HizliAnaliz'
import { TahminGecmisi } from './pages/TahminGecmisi'
import { KaliciDegerlendirme } from './pages/KaliciDegerlendirme'
import { TahminDetay } from './pages/TahminDetay'
import { Login } from './pages/Login'
import './app/styles.css'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <KorumaliUygulama />
      </BrowserRouter>
    </AuthProvider>
  )
}

function KorumaliUygulama() {
  const { kullanici, yukleniyor } = useAuth()

  if (yukleniyor) {
    return (
      <main className="sayfa">
        <p role="status">Oturum yükleniyor…</p>
      </main>
    )
  }

  if (!kullanici) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  return (
    <Routes>
      <Route path="/app" element={<AppShell />}>
        <Route index element={<Dashboard />} />
        <Route path="analiz" element={<HizliAnaliz />} />
        <Route path="tahminler" element={<TahminGecmisi />} />
        <Route path="tahminler/yeni" element={<KaliciDegerlendirme />} />
        <Route path="tahminler/:tahminId" element={<TahminDetay />} />
      </Route>
      <Route path="/login" element={<Navigate to="/app" replace />} />
      <Route path="/" element={<Navigate to="/app" replace />} />
      <Route path="*" element={<Navigate to="/app" replace />} />
    </Routes>
  )
}
