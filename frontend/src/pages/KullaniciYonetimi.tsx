import { useEffect, useState, useCallback } from 'react'
import { UserCheck, UserPlus, KeyRound, X } from 'lucide-react'
import { kullanicilariGetir, kullaniciOlustur, kullaniciGuncelle, kullaniciSifreSifirla } from '../api/yonetim'
import { useAuth } from '../app/AuthContext'
import { ApiHatasi } from '../types/apiHata'
import { LoadingSkeleton } from '../components/feedback/LoadingSkeleton'
import { ErrorState } from '../components/feedback/ErrorState'
import { useAccessibleDialog } from '../components/accessibility/useAccessibleDialog'
import { rolMetni } from '../types/tahminler'
import type { KullaniciYonetimItem } from '../types/yonetim'

const PAROLA_YARDIMI = 'En az 8 karakter; yaygın, tamamen sayısal veya kullanıcı bilgilerine çok benzeyen parolalar kabul edilmez.'

function alanHatasiniGetir(hata: ApiHatasi, alan: string): string {
  const deger = hata.alanlar[alan]
  if (Array.isArray(deger)) return deger.map(String).join(' ')
  if (typeof deger === 'string') return deger
  return hata.message
}

export function KullaniciYonetimi() {
  const { kullanici } = useAuth()
  const isAdmin = kullanici?.rol === 'ADMIN'

  const [yukleniyor, setYukleniyor] = useState(true)
  const [hata, setHata] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)
  const [kullanicilar, setKullanicilar] = useState<KullaniciYonetimItem[]>([])

  // Modal State: Yeni Kullanıcı
  const [yeniModalAcik, setYeniModalAcik] = useState(false)
  const [yeniUsername, setYeniUsername] = useState('')
  const [yeniEmail, setYeniEmail] = useState('')
  const [yeniPassword, setYeniPassword] = useState('')
  const [yeniRol, setYeniRol] = useState<'ADMIN' | 'USER'>('USER')
  const [islemYukleniyor, setIslemYukleniyor] = useState(false)
  const [formHata, setFormHata] = useState<string | null>(null)

  // Modal State: Şifre Sıfırlama
  const [sifreModalAcik, setSifreModalAcik] = useState(false)
  const [seciliKullanici, setSeciliKullanici] = useState<KullaniciYonetimItem | null>(null)
  const [yeniSifre, setYeniSifre] = useState('')
  const [sifreHata, setSifreHata] = useState<string | null>(null)
  const [basariMesaji, setBasariMesaji] = useState<string | null>(null)
  const yeniDialog = useAccessibleDialog(yeniModalAcik, () => setYeniModalAcik(false))
  const sifreDialog = useAccessibleDialog(sifreModalAcik, () => setSifreModalAcik(false))

  const yukleData = useCallback(() => {
    setYukleniyor(true)
    setHata(null)
    kullanicilariGetir()
      .then((res) => {
        setKullanicilar(res)
        setYukleniyor(false)
      })
      .catch((err) => {
        if (err instanceof ApiHatasi) {
          setHata(err.message)
          setTraceId(err.traceId ?? null)
        } else {
          setHata('Kullanıcı listesi yüklenirken bir hata oluştu.')
        }
        setYukleniyor(false)
      })
  }, [])

  useEffect(() => {
    let unmounted = false
    kullanicilariGetir()
      .then((res) => {
        if (!unmounted) {
          setKullanicilar(res)
          setYukleniyor(false)
        }
      })
      .catch((err) => {
        if (!unmounted) {
          if (err instanceof ApiHatasi) {
            setHata(err.message)
            setTraceId(err.traceId ?? null)
          } else {
            setHata('Kullanıcı listesi yüklenirken bir hata oluştu.')
          }
          setYukleniyor(false)
        }
      })

    return () => {
      unmounted = true
    }
  }, [])

  const handleYeniKullaniciSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormHata(null)
    if (!yeniUsername.trim() || !yeniPassword.trim()) {
      setFormHata('Kullanıcı adı ve parola zorunludur.')
      return
    }
    if (yeniPassword.length < 8) {
      setFormHata('Parola en az 8 karakter olmalıdır.')
      return
    }

    setIslemYukleniyor(true)
    try {
      await kullaniciOlustur({
        username: yeniUsername.trim(),
        email: yeniEmail.trim() || undefined,
        password: yeniPassword,
        rol: yeniRol,
        is_active: true,
      })
      setYeniModalAcik(false)
      setYeniUsername('')
      setYeniEmail('')
      setYeniPassword('')
      setYeniRol('USER')
      setBasariMesaji('Yeni kullanıcı başarıyla eklendi.')
      yukleData()
    } catch (err) {
      if (err instanceof ApiHatasi) {
        setFormHata(alanHatasiniGetir(err, 'password'))
      } else {
        setFormHata('Kullanıcı oluşturulurken bir hata oluştu.')
      }
    } finally {
      setIslemYukleniyor(false)
    }
  }

  const handleAktiflikToggle = async (targetUser: KullaniciYonetimItem) => {
    try {
      await kullaniciGuncelle(targetUser.id, { is_active: !targetUser.is_active })
      setBasariMesaji(`"${targetUser.username}" kullanıcısının aktiflik durumu güncellendi.`)
      yukleData()
    } catch (err) {
      if (err instanceof ApiHatasi) {
        setHata(err.message)
      } else {
        setHata('Aktiflik durumu değiştirilirken hata oluştu.')
      }
    }
  }

  const handleSifreSifirlaSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!seciliKullanici) return
    setSifreHata(null)
    if (!yeniSifre || yeniSifre.length < 8) {
      setSifreHata('Yeni parola en az 8 karakter olmalıdır.')
      return
    }

    setIslemYukleniyor(true)
    try {
      await kullaniciSifreSifirla(seciliKullanici.id, yeniSifre)
      setSifreModalAcik(false)
      setSeciliKullanici(null)
      setYeniSifre('')
      setBasariMesaji(`"${seciliKullanici.username}" kullanıcısının parolası sıfırlandı.`)
    } catch (err) {
      if (err instanceof ApiHatasi) {
        setSifreHata(alanHatasiniGetir(err, 'yeni_sifre'))
      } else {
        setSifreHata('Parola sıfırlanırken hata oluştu.')
      }
    } finally {
      setIslemYukleniyor(false)
    }
  }

  if (!isAdmin) {
    return (
      <div className="sayfa-konteyner">
        <ErrorState mesaj="Bu alanı görüntülemek için YÖNETİCİ (ADMIN) yetkisi gereklidir." />
      </div>
    )
  }

  return (
    <div className="sayfa-konteyner">
      <div className="sayfa-baslik-alani" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 className="sayfa-basligi">Kullanıcı Yönetimi</h1>
          <p className="sayfa-alt-basligi">
            Sistemdeki kullanıcıları inceleyin, yeni kullanıcı ekleyin, rolleri ve aktiflik durumlarını yönetin.
          </p>
        </div>

        <button
          type="button"
          className="buton birincil"
          onClick={() => setYeniModalAcik(true)}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
        >
          <UserPlus size={18} />
          <span>Yeni Kullanıcı</span>
        </button>
      </div>

      {basariMesaji && (
        <div style={{ padding: '12px 16px', marginBottom: '16px', background: 'var(--status-success-bg, #ecfdf5)', color: 'var(--status-success-text, #065f46)', borderRadius: '8px', border: '1px solid var(--status-success-border, #a7f3d0)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{basariMesaji}</span>
          <button type="button" style={{ background: 'none', border: 'none', cursor: 'pointer' }} onClick={() => setBasariMesaji(null)}>
            <X size={16} />
          </button>
        </div>
      )}

      {yukleniyor ? (
        <LoadingSkeleton adet={4} />
      ) : hata ? (
        <ErrorState mesaj={hata} traceId={traceId} onRetry={yukleData} />
      ) : (
        <div className="dashboard-panel">
          <div className="tablo-konteyner">
            <table className="tablo">
              <caption className="sr-only">Sistem kullanıcıları ve yönetim işlemleri</caption>
              <thead>
                <tr>
                  <th scope="col">Kullanıcı Adı</th>
                  <th scope="col">E-Posta</th>
                  <th scope="col">Sistem Rolü</th>
                  <th scope="col">Durum</th>
                  <th scope="col">Kayıt Tarihi</th>
                  <th scope="col" style={{ textAlign: 'right' }}>Aksiyonlar</th>
                </tr>
              </thead>
              <tbody>
                {kullanicilar.map((u) => (
                  <tr key={u.id}>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
                        <UserCheck size={16} color="var(--brand-primary)" />
                        <span>{u.username}</span>
                      </div>
                    </td>
                    <td>{u.email || '-'}</td>
                    <td>
                      <span className={`rozet ${u.rol === 'ADMIN' ? 'kritik' : 'bilgi'}`}>
                        {rolMetni(u.rol)}
                      </span>
                    </td>
                    <td>
                      <span className={`rozet ${u.is_active ? 'basarili' : 'nodum'}`}>
                        {u.is_active ? 'Aktif' : 'Pasif'}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                      {new Date(u.date_joined).toLocaleDateString('tr-TR')}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '8px' }}>
                        <button
                          type="button"
                          className="buton ikincil kucuk"
                          onClick={() => {
                            setSeciliKullanici(u)
                            setSifreModalAcik(true)
                          }}
                          title="Şifre Sıfırla"
                          style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                        >
                          <KeyRound size={14} />
                          <span>Şifre Güncelle</span>
                        </button>

                        <button
                          type="button"
                          className={`buton ${u.is_active ? 'tehlike' : 'birincil'} kucuk`}
                          onClick={() => handleAktiflikToggle(u)}
                        >
                          {u.is_active ? 'Pasife Al' : 'Aktif Et'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal: Yeni Kullanıcı */}
      {yeniModalAcik && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div {...yeniDialog} role="dialog" aria-modal="true" aria-labelledby="yeni-kullanici-basligi" style={{ background: 'var(--bg-surface, #ffffff)', padding: '24px', borderRadius: '12px', width: '100%', maxWidth: '440px', maxHeight: 'calc(100vh - 32px)', overflowY: 'auto', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 id="yeni-kullanici-basligi" style={{ margin: 0 }}>Yeni Kullanıcı Tanımla</h3>
              <button type="button" aria-label="Yeni kullanıcı penceresini kapat" style={{ background: 'none', border: 'none', cursor: 'pointer' }} onClick={() => setYeniModalAcik(false)}>
                <X size={20} />
              </button>
            </div>

            {formHata && (
              <div role="alert" style={{ padding: '10px 12px', marginBottom: '12px', background: 'var(--status-danger-bg, #fef2f2)', color: 'var(--status-danger-text, #991b1b)', borderRadius: '6px', fontSize: '0.88rem' }}>
                {formHata}
              </div>
            )}

            <form onSubmit={handleYeniKullaniciSubmit}>
              <div className="form-grubu" style={{ marginBottom: '12px' }}>
                <label className="form-etiketi" htmlFor="yeni-kullanici-adi">Kullanıcı Adı *</label>
                <input
                  id="yeni-kullanici-adi"
                  data-dialog-initial-focus
                  type="text"
                  className="form-girdisi"
                  value={yeniUsername}
                  onChange={(e) => setYeniUsername(e.target.value)}
                  placeholder="ör. ahmet.yilmaz"
                  required
                />
              </div>

              <div className="form-grubu" style={{ marginBottom: '12px' }}>
                <label className="form-etiketi" htmlFor="yeni-kullanici-email">E-Posta</label>
                <input
                  id="yeni-kullanici-email"
                  type="email"
                  className="form-girdisi"
                  value={yeniEmail}
                  onChange={(e) => setYeniEmail(e.target.value)}
                  placeholder="ahmet@fabrika.com"
                />
              </div>

              <div className="form-grubu" style={{ marginBottom: '12px' }}>
                <label className="form-etiketi" htmlFor="yeni-kullanici-parolasi">İlk Parola *</label>
                <input
                  id="yeni-kullanici-parolasi"
                  type="password"
                  className="form-girdisi"
                  value={yeniPassword}
                  onChange={(e) => setYeniPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  minLength={8}
                  autoComplete="new-password"
                  aria-describedby="yeni-parola-yardimi"
                />
                <small id="yeni-parola-yardimi">{PAROLA_YARDIMI}</small>
              </div>

              <div className="form-grubu" style={{ marginBottom: '20px' }}>
                <label className="form-etiketi" htmlFor="yeni-kullanici-rolu">Sistem Rolü *</label>
                <select
                  id="yeni-kullanici-rolu"
                  className="form-girdisi"
                  value={yeniRol}
                  onChange={(e) => setYeniRol(e.target.value as 'ADMIN' | 'USER')}
                >
                  <option value="USER">Operatör (USER)</option>
                  <option value="ADMIN">Yönetici (ADMIN)</option>
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                <button type="button" className="buton ikincil" onClick={() => setYeniModalAcik(false)}>
                  İptal
                </button>
                <button type="submit" className="buton birincil" disabled={islemYukleniyor}>
                  {islemYukleniyor ? 'Kaydediliyor…' : 'Oluştur'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Şifre Sıfırla */}
      {sifreModalAcik && seciliKullanici && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div {...sifreDialog} role="dialog" aria-modal="true" aria-labelledby="parola-sifirlama-basligi" style={{ background: 'var(--bg-surface, #ffffff)', padding: '24px', borderRadius: '12px', width: '100%', maxWidth: '400px', maxHeight: 'calc(100vh - 32px)', overflowY: 'auto', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 id="parola-sifirlama-basligi" style={{ margin: 0 }}>Parola Sıfırla</h3>
              <button type="button" aria-label="Parola sıfırlama penceresini kapat" style={{ background: 'none', border: 'none', cursor: 'pointer' }} onClick={() => setSifreModalAcik(false)}>
                <X size={20} />
              </button>
            </div>

            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
              <strong>{seciliKullanici.username}</strong> kullanıcısı için yeni bir parola tanımlayın.
            </p>

            {sifreHata && (
              <div role="alert" style={{ padding: '10px 12px', marginBottom: '12px', background: 'var(--status-danger-bg, #fef2f2)', color: 'var(--status-danger-text, #991b1b)', borderRadius: '6px', fontSize: '0.88rem' }}>
                {sifreHata}
              </div>
            )}

            <form onSubmit={handleSifreSifirlaSubmit}>
              <div className="form-grubu" style={{ marginBottom: '20px' }}>
                <label className="form-etiketi" htmlFor="sifirlama-parolasi">Yeni Parola *</label>
                <input
                  id="sifirlama-parolasi"
                  data-dialog-initial-focus
                  type="password"
                  className="form-girdisi"
                  value={yeniSifre}
                  onChange={(e) => setYeniSifre(e.target.value)}
                  placeholder="En az 8 karakter"
                  required
                  minLength={8}
                  autoComplete="new-password"
                  aria-describedby="sifirlama-parola-yardimi"
                />
                <small id="sifirlama-parola-yardimi">{PAROLA_YARDIMI}</small>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                <button type="button" className="buton ikincil" onClick={() => setSifreModalAcik(false)}>
                  İptal
                </button>
                <button type="submit" className="buton birincil" disabled={islemYukleniyor}>
                  {islemYukleniyor ? 'Güncelleniyor…' : 'Parolayı Güncelle'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
