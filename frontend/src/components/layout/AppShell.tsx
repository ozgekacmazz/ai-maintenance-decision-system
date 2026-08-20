import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Header } from './Header'

export function AppShell() {
  const [sidebarAcik, setSidebarAcik] = useState(false)

  return (
    <div className="app-shell">
      <a className="skip-link" href="#ana-icerik">İçeriğe geç</a>
      <Sidebar acik={sidebarAcik} onKapat={() => setSidebarAcik(false)} />
      <div className="app-ana-icerik">
        <Header
          sidebarAcik={sidebarAcik}
          onToggleSidebar={() => setSidebarAcik(!sidebarAcik)}
        />
        <main id="ana-icerik" className="sayfa-icerik" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
