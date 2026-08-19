import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './app/AuthContext'
import { AppShell } from './components/layout/AppShell'
import { Dashboard } from './pages/Dashboard'
import { HizliAnaliz } from './pages/HizliAnaliz'
import { TahminGecmisi } from './pages/TahminGecmisi'
import { KaliciDegerlendirme } from './pages/KaliciDegerlendirme'
import { TahminDetay } from './pages/TahminDetay'
import { IsEmirleri } from './pages/IsEmirleri'
import { IsEmriDetay } from './pages/IsEmriDetay'
import { ReplayListesi } from './pages/ReplayListesi'
import { ReplayDetay } from './pages/ReplayDetay'
import { MakineYonetimi } from './pages/MakineYonetimi'
import { StokYonetimi } from './pages/StokYonetimi'
import { KullaniciYonetimi } from './pages/KullaniciYonetimi'
import { TahminLoglari } from './pages/TahminLoglari'
import { AdminRoute } from './components/routing/AdminRoute'
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
        <Route path="is-emirleri" element={<IsEmirleri />} />
        <Route path="is-emirleri/:isEmriId" element={<IsEmriDetay />} />
        <Route path="replay" element={<ReplayListesi />} />
        <Route path="replay/:sessionId" element={<ReplayDetay />} />
        <Route path="yonetim" element={<AdminRoute />}>
          <Route path="makineler" element={<MakineYonetimi />} />
          <Route path="stok" element={<StokYonetimi />} />
          <Route path="kullanicilar" element={<KullaniciYonetimi />} />
          <Route path="tahmin-loglari" element={<TahminLoglari />} />
        </Route>
      </Route>
      <Route path="/login" element={<Navigate to="/app" replace />} />
      <Route path="/" element={<Navigate to="/app" replace />} />
      <Route path="*" element={<Navigate to="/app" replace />} />
    </Routes>
  )
}
