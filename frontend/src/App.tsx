import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './app/AuthContext'
import { AppShell } from './components/layout/AppShell'
import { AdminRoute } from './components/routing/AdminRoute'
import './app/styles.css'

const Dashboard = lazy(() => import('./pages/Dashboard').then((module) => ({ default: module.Dashboard })))
const HizliAnaliz = lazy(() => import('./pages/HizliAnaliz').then((module) => ({ default: module.HizliAnaliz })))
const TahminGecmisi = lazy(() => import('./pages/TahminGecmisi').then((module) => ({ default: module.TahminGecmisi })))
const KaliciDegerlendirme = lazy(() => import('./pages/KaliciDegerlendirme').then((module) => ({ default: module.KaliciDegerlendirme })))
const TahminDetay = lazy(() => import('./pages/TahminDetay').then((module) => ({ default: module.TahminDetay })))
const IsEmirleri = lazy(() => import('./pages/IsEmirleri').then((module) => ({ default: module.IsEmirleri })))
const IsEmriDetay = lazy(() => import('./pages/IsEmriDetay').then((module) => ({ default: module.IsEmriDetay })))
const ReplayListesi = lazy(() => import('./pages/ReplayListesi').then((module) => ({ default: module.ReplayListesi })))
const ReplayDetay = lazy(() => import('./pages/ReplayDetay').then((module) => ({ default: module.ReplayDetay })))
const MakineYonetimi = lazy(() => import('./pages/MakineYonetimi').then((module) => ({ default: module.MakineYonetimi })))
const StokYonetimi = lazy(() => import('./pages/StokYonetimi').then((module) => ({ default: module.StokYonetimi })))
const KullaniciYonetimi = lazy(() => import('./pages/KullaniciYonetimi').then((module) => ({ default: module.KullaniciYonetimi })))
const TahminLoglari = lazy(() => import('./pages/TahminLoglari').then((module) => ({ default: module.TahminLoglari })))
const Login = lazy(() => import('./pages/Login').then((module) => ({ default: module.Login })))

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Suspense fallback={<main className="sayfa"><p role="status">Sayfa yükleniyor…</p></main>}>
          <KorumaliUygulama />
        </Suspense>
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
