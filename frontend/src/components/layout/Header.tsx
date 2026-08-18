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
  if (location.pathname.startsWith('/app/analiz')) {
    sayfaBasligi = 'Hızlı Sensör Analizi'
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
