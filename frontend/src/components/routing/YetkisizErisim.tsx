import { Link } from 'react-router-dom'

export function YetkisizErisim() {
  return (
    <section className="empty-state" aria-labelledby="yetkisiz-baslik">
      <h1 id="yetkisiz-baslik">Bu bölüme erişim yetkiniz yok</h1>
      <p>Bu sayfa yalnızca yöneticiler tarafından görüntülenebilir.</p>
      <Link className="buton-primer empty-state-butonu" to="/app">
        Ana sayfaya dön
      </Link>
    </section>
  )
}
