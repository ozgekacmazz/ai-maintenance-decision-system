import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Activity, Cpu } from 'lucide-react'
import { useAuth } from '../../app/AuthContext'
import { rolMetni } from '../../types/tahminler'

interface SidebarProps {
  acik: boolean
  onKapat: () => void
}

export function Sidebar({ acik, onKapat }: SidebarProps) {
  const { kullanici } = useAuth()

  return (
    <aside className={`sidebar ${acik ? 'open' : ''}`}>
      <div className="sidebar-ust">
        <div className="sidebar-logo">
          <Cpu size={22} />
        </div>
        <div className="sidebar-baslik">
          <span className="sidebar-baslik-ana">Bakım Karar</span>
          <span className="sidebar-baslik-alt">Endüstriyel AI</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <NavLink
          to="/app"
          end
          className={({ isActive }) => (isActive ? 'nav-link aktif' : 'nav-link')}
          onClick={onKapat}
        >
          <LayoutDashboard size={18} />
          <span>Genel Bakış</span>
        </NavLink>

        <NavLink
          to="/app/analiz"
          className={({ isActive }) => (isActive ? 'nav-link aktif' : 'nav-link')}
          onClick={onKapat}
        >
          <Activity size={18} />
          <span>Hızlı Analiz</span>
        </NavLink>
      </nav>

      <div className="sidebar-alt">
        <div className="sidebar-profil-kart">
          <div className="profil-avataresi">
            {kullanici?.username ? kullanici.username.charAt(0).toUpperCase() : 'K'}
          </div>
          <div className="profil-bilgisi">
            <span className="profil-adi">{kullanici?.username ?? 'Kullanıcı'}</span>
            <span className="profil-rol">{rolMetni(kullanici?.rol)}</span>
          </div>
        </div>
      </div>
    </aside>
  )
}
