import { useState, type FormEvent } from 'react'
import { Cpu, Eye, EyeOff, ShieldCheck, ArrowRight } from 'lucide-react'

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
      if (error instanceof ApiHatasi) {
        setHata(error.message || 'Giriş bilgileri doğrulanamadı.')
        setAlanHatalari(error.alanlar || {})
      } else {
        setHata(error instanceof Error ? error.message : 'Giriş işlemi tamamlanamadı.')
      }
    } finally {
      setGonderiliyor(false)
    }
  }

  return (
    <main className="login-sayfasi">
      <div className="login-konteyner">
        {/* Sol Marka ve Görsel Alan */}
        <div className="login-gorsel-alani">
          <div className="login-marka">
            <div className="login-marka-ikon">
              <Cpu size={24} color="#ffffff" />
            </div>
            <span>Bakım Karar Sistemi</span>
          </div>

          <div className="login-hero-metin">
            <h2>Endüstriyel AI İle Makine Sağlığını Yönetin</h2>
            <p>
              Sensör verilerinden anlık arıza riski üretin, bakım kararlarını önceliklendirin ve üretimi kesintisiz sürdürün.
            </p>

            <svg
              className="login-dekoratif-svg"
              viewBox="0 0 400 140"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <path
                d="M10 90 Q 75 30, 150 70 T 300 50 T 390 80"
                stroke="rgba(255, 255, 255, 0.25)"
                strokeWidth="3"
                fill="none"
              />
              <path
                d="M10 70 Q 100 110, 200 40 T 390 90"
                stroke="rgba(13, 148, 136, 0.4)"
                strokeWidth="2"
                fill="none"
              />
              <circle cx="150" cy="70" r="5" fill="#3b82f6" />
              <circle cx="300" cy="50" r="5" fill="#0d9488" />
              <circle cx="200" cy="40" r="4" fill="#ffffff" />
            </svg>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', color: '#94a3b8' }}>
            <ShieldCheck size={16} color="#0d9488" />
            <span>Güvenli Kurumsal Erişim</span>
          </div>
        </div>

        {/* Sağ Form Alanı */}
        <div className="login-form-alani">
          <div className="login-form-baslik">
            <h1>Hesabınıza giriş yapın</h1>
            <p>Makine sağlığı ve bakım kararlarını tek merkezden takip edin.</p>
          </div>

          <form onSubmit={(event) => void submit(event)}>
            <div>
              <label htmlFor="username">Kullanıcı adı</label>
              <input
                id="username"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Kullanıcı adınızı girin"
              />
              {Boolean(alanHatalari.username) && (
                <p className="alan-hatasi">Kullanıcı adını kontrol edin.</p>
              )}
            </div>

            <div>
              <label htmlFor="password">Parola</label>
              <div className="parola-alani">
                <input
                  id="password"
                  type={gorunur ? 'text' : 'password'}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Parolanızı girin"
                />
                <button
                  className="goz"
                  type="button"
                  aria-label={gorunur ? 'Parolayı gizle' : 'Parolayı göster'}
                  onClick={() => setGorunur(!gorunur)}
                >
                  {gorunur ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              {Boolean(alanHatalari.password) && (
                <p className="alan-hatasi">Parolayı kontrol edin.</p>
              )}
            </div>

            {hata && (
              <p role="alert" className="hata">
                {hata}
              </p>
            )}

            <button type="submit" disabled={gonderiliyor} style={{ marginTop: '8px' }}>
              {gonderiliyor ? (
                'Giriş yapılıyor…'
              ) : (
                <>
                  <span>Giriş yap</span>
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    </main>
  )
}
