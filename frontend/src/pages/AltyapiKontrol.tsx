import { useCallback, useEffect, useState } from 'react'

import { saglikDurumunuGetir } from '../api/saglik'
import type { SaglikYaniti } from '../types/saglik'
import { adminKontrolu } from '../api/auth'
import { useAuth } from '../app/AuthContext'

export function AltyapiKontrol() {
  const { kullanici, cikis } = useAuth()
  const [saglik, setSaglik] = useState<SaglikYaniti | null>(null)
  const [yukleniyor, setYukleniyor] = useState(true)
  const [hata, setHata] = useState<string | null>(null)
  const [adminSonucu, setAdminSonucu] = useState<string | null>(null)

  const kontrolEt = useCallback(async () => {
    setYukleniyor(true)
    setHata(null)
    try {
      setSaglik(await saglikDurumunuGetir())
    } catch {
      setSaglik(null)
      setHata('Backend bağlantısı kurulamadı. Servisleri kontrol edip tekrar deneyin.')
    } finally {
      setYukleniyor(false)
    }
  }, [])

  useEffect(() => {
    let aktif = true
    saglikDurumunuGetir()
      .then((yanit) => {
        if (aktif) setSaglik(yanit)
      })
      .catch(() => {
        if (aktif) setHata('Backend bağlantısı kurulamadı. Servisleri kontrol edip tekrar deneyin.')
      })
      .finally(() => {
        if (aktif) setYukleniyor(false)
      })
    return () => {
      aktif = false
    }
  }, [])

  return (
    <main className="sayfa">
      <section className="kart">
        <p className="urun">AI Destekli Bakım Karar Sistemi</p>
        <h1>Sprint 1 Altyapı Kontrolü</h1>
        <p className="aciklama">Uygulama bileşenlerinin bağlantı durumunu görüntüleyin.</p>
        <p>Oturum: <strong>{kullanici?.username}</strong> · {kullanici?.rol}</p>

        <div className="durum-listesi">
          <DurumSatiri etiket="Frontend" durum="çalışıyor" basarili />
          <DurumSatiri
            etiket="Backend"
            durum={yukleniyor ? 'kontrol ediliyor' : saglik ? 'bağlı' : 'bağlantı yok'}
            basarili={Boolean(saglik)}
          />
          <DurumSatiri
            etiket="PostgreSQL"
            durum={yukleniyor ? 'kontrol ediliyor' : saglik?.veritabani === 'bagli' ? 'bağlı' : 'bağlantı yok'}
            basarili={saglik?.veritabani === 'bagli'}
          />
        </div>

        {yukleniyor && <p role="status" className="bilgi">Bağlantılar kontrol ediliyor…</p>}
        {hata && <p role="alert" className="hata">{hata}</p>}
        <button type="button" onClick={() => void kontrolEt()} disabled={yukleniyor}>
          Tekrar dene
        </button>
        <button className="ikincil" type="button" onClick={() => void adminKontrolu().then((sonuc) => setAdminSonucu(sonuc === 'izinli' ? 'Admin erişimi doğrulandı.' : 'Bu alan için ADMIN rolü gerekiyor.')).catch(() => setAdminSonucu('Kontrol tamamlanamadı.'))}>Admin erişimini kontrol et</button>
        {adminSonucu && <p role="status">{adminSonucu}</p>}
        <button className="ikincil" type="button" onClick={() => void cikis()}>Çıkış yap</button>
      </section>
    </main>
  )
}

function DurumSatiri({ etiket, durum, basarili }: { etiket: string; durum: string; basarili: boolean }) {
  return (
    <div className="durum-satiri">
      <span>{etiket}</span>
      <span className={basarili ? 'rozet basarili' : 'rozet'}>{durum}</span>
    </div>
  )
}
