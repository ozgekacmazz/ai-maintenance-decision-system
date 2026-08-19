import { useLocation } from 'react-router-dom'
import { Menu, X, LogOut, ShieldCheck } from 'lucide-react'
import { useAuth } from '../../app/AuthContext'
import { rolMetni } from '../../types/tahminler'

interface HeaderProps {
  sidebarAcik: boolean
  onToggleSidebar: () => void
}

export function Header({ sidebarAcik, onToggleSidebar }: HeaderProps) {
  const { kullanici, cikis } = useAuth()
  const location = useLocation()

  let sayfaBasligi = 'Genel Bakış'
  const path = location.pathname

  if (path === '/app/analiz') {
    sayfaBasligi = 'Hızlı Sensör Analizi'
  } else if (path === '/app/tahminler/yeni') {
    sayfaBasligi = 'Yeni Kalıcı Değerlendirme'
  } else if (path === '/app/tahminler') {
    sayfaBasligi = 'Tahmin Geçmişi'
  } else if (path.startsWith('/app/tahminler/')) {
    sayfaBasligi = 'Değerlendirme Detayı'
  } else if (path === '/app/is-emirleri') {
    sayfaBasligi = 'İş Emirleri'
  } else if (path.startsWith('/app/is-emirleri/')) {
    sayfaBasligi = 'İş Emri Detayı'
  } else if (path === '/app/replay') {
    sayfaBasligi = 'Sensör Replay'
  } else if (path.startsWith('/app/replay/')) {
    sayfaBasligi = 'Replay Oturumu'
  } else if (path === '/app/yonetim/makineler') {
    sayfaBasligi = 'Makine Yönetimi'
  } else if (path === '/app/yonetim/stok') {
    sayfaBasligi = 'Stok Yönetimi'
  } else if (path === '/app/yonetim/kullanicilar') {
    sayfaBasligi = 'Kullanıcı Yönetimi'
  } else if (path === '/app/altyapi') {
    sayfaBasligi = 'Altyapı Kontrolü'
  }

  return (
    <header className="header">
      <div className="header-sol">
        <button
          className="mobile-toggle"
          type="button"
          aria-label={sidebarAcik ? 'Menüyü kapat' : 'Menüyü aç'}
          onClick={onToggleSidebar}
        >
          {sidebarAcik ? <X size={20} /> : <Menu size={20} />}
        </button>
        <h1 className="header-sayfa-basligi">{sayfaBasligi}</h1>
      </div>

      <div className="header-sag">
        <span className="rozet bilgi" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
          <ShieldCheck size={14} />
          {rolMetni(kullanici?.rol)}
        </span>

        <span style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
          {kullanici?.username}
        </span>

        <button
          className="header-cikis-butonu"
          type="button"
          onClick={() => void cikis()}
        >
          <LogOut size={16} />
          <span>Çıkış Yap</span>
        </button>
      </div>
    </header>
  )
}
