import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Activity,
  Cpu,
  History,
  Wrench,
  PlayCircle,
  Building2,
  Package,
  UserCheck,
  FileText,
} from 'lucide-react'
import { useAuth } from '../../app/AuthContext'
import { rolMetni } from '../../types/tahminler'
import { adminMi } from '../../app/roles'

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

        <NavLink
          to="/app/tahminler"
          className={({ isActive }) => (isActive ? 'nav-link aktif' : 'nav-link')}
          onClick={onKapat}
        >
          <History size={18} />
          <span>Tahmin Geçmişi</span>
        </NavLink>

        <NavLink
          to="/app/is-emirleri"
          className={({ isActive }) => (isActive ? 'nav-link aktif' : 'nav-link')}
          onClick={onKapat}
        >
          <Wrench size={18} />
          <span>İş Emirleri</span>
        </NavLink>

        {adminMi(kullanici) && (
          <>
            <div style={{ marginTop: '16px', padding: '0 12px 6px', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Yönetim
            </div>

            <NavLink
              to="/app/replay"
              className={({ isActive }) => (isActive ? 'nav-link aktif' : 'nav-link')}
              onClick={onKapat}
            >
              <PlayCircle size={18} />
              <span>Sensör Replay</span>
            </NavLink>

            <NavLink
              to="/app/yonetim/makineler"
              className={({ isActive }) => (isActive ? 'nav-link aktif' : 'nav-link')}
              onClick={onKapat}
            >
              <Building2 size={18} />
              <span>Makine Yönetimi</span>
            </NavLink>

            <NavLink
              to="/app/yonetim/stok"
              className={({ isActive }) => (isActive ? 'nav-link aktif' : 'nav-link')}
              onClick={onKapat}
            >
              <Package size={18} />
              <span>Stok Yönetimi</span>
            </NavLink>

            <NavLink
              to="/app/yonetim/kullanicilar"
              className={({ isActive }) => (isActive ? 'nav-link aktif' : 'nav-link')}
              onClick={onKapat}
            >
              <UserCheck size={18} />
              <span>Kullanıcı Yönetimi</span>
            </NavLink>

            <NavLink
              to="/app/yonetim/tahmin-loglari"
              className={({ isActive }) => (isActive ? 'nav-link aktif' : 'nav-link')}
              onClick={onKapat}
            >
              <FileText size={18} />
              <span>Tahmin Logları</span>
            </NavLink>
          </>
        )}
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
