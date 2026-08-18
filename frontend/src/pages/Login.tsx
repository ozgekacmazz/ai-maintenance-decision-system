import { useState, type FormEvent } from 'react'

import { useAuth } from '../app/AuthContext'
import { ApiHatasi } from '../types/apiHata'

export function Login() {
  const { giris } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [gorunur, setGorunur] = useState(false)
  const [gonderiliyor, setGonderiliyor] = useState(false)
  const [hata, setHata] = useState<string | null>(null)
  const [alanHatalari, setAlanHatalari] = useState<Record<string, unknown>>({})

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!username.trim() || !password) {
      setHata('Kullanıcı adı ve parola zorunludur.')
      return
    }
    setGonderiliyor(true)
    setHata(null)
    setAlanHatalari({})
    try {
      await giris(username, password)
    } catch (error) {
      setHata(error instanceof Error ? error.message : 'Giriş işlemi tamamlanamadı.')
      if (error instanceof ApiHatasi) setAlanHatalari(error.alanlar)
    } finally {
      setGonderiliyor(false)
    }
  }

  return (
    <main className="sayfa">
      <section className="kart login-kart">
        <p className="urun">AI Destekli Bakım Karar Sistemi</p>
        <h1>Güvenli giriş</h1>
        <p className="aciklama">Bakım karar sistemine kullanıcı bilgilerinizle erişin.</p>
        <form onSubmit={(event) => void submit(event)}>
          <label htmlFor="username">Kullanıcı adı</label>
          <input id="username" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} />
          {Boolean(alanHatalari.username) && <p className="alan-hatasi">Kullanıcı adını kontrol edin.</p>}
          <label htmlFor="password">Parola</label>
          <div className="parola-alani">
            <input id="password" type={gorunur ? 'text' : 'password'} autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
            <button className="goz" type="button" aria-label={gorunur ? 'Parolayı gizle' : 'Parolayı göster'} onClick={() => setGorunur(!gorunur)}>{gorunur ? 'Gizle' : 'Göster'}</button>
          </div>
          {Boolean(alanHatalari.password) && <p className="alan-hatasi">Parolayı kontrol edin.</p>}
          {hata && <p role="alert" className="hata">{hata}</p>}
          <button type="submit" disabled={gonderiliyor}>{gonderiliyor ? 'Giriş yapılıyor…' : 'Giriş yap'}</button>
        </form>
      </section>
    </main>
  )
}
