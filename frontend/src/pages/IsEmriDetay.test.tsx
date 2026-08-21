import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { IsEmriDetay } from './IsEmriDetay'
import * as isEmirleriApi from '../api/isEmirleri'
import * as authContext from '../app/AuthContext'
import type { IsEmriDetay as IsEmriDetayType } from '../types/isEmirleri'
import * as yonetimApi from '../api/yonetim'

afterEach(() => {
  vi.restoreAllMocks()
})

const MOCK_WO_DETAIL: IsEmriDetayType = {
  id: 'wo-101',
  is_emri_numarasi: 'WO-20260819-001',
  tahmin_kaydi_id: 'pred-101',
  makine: { id: 1, kod: 'M-101', ad: 'Pres Motoru 1' },
  ana_aksiyon: 'ACIL_TEKNIK_DEGERLENDIRME',
  durum: 'ACIK',
  etkin_oncelik_seviyesi: 'KRITIK',
  kaynak_oncelik_seviyesi: 'KRITIK',
  kaynak_genel_oncelik: 5,
  kaynak_genel_oncelik_formul_surumu: 'general-priority-1.0.0',
  etkin_genel_oncelik: 5,
  atanan_kullanici: { id: 5, kullanici_adi: 'ahmet.bakim' },
  hedef_mudahale_zamani: '2026-08-19T14:00:00Z',
  gecikmis: false,
  olcum_zamani: '2026-08-19T10:00:00Z',
  olusturan: { id: 2, kullanici_adi: 'ozge.06' },
  olusturulma_zamani: '2026-08-19T10:05:00Z',
  version: 1,
  baslik: 'Pres Motoru Yüksek Sıcaklık Kontrolü',
  aciklama: 'Model risk eşiği aşıldı, rulman ve yağ seviyesi incelenmeli.',
  politika_surumu: 'work-order-policy-1.0.0',
  kaynak_karar: {
    motor_surumu: 'maintenance-priority-1.0.0',
    teknik_aciliyet_skoru: 90,
    tedarik_riski_skoru: 20,
    nihai_oncelik_skoru: 85,
    oncelik_seviyesi: 'KRITIK',
    ana_aksiyon: 'ACIL_TEKNIK_DEGERLENDIRME',
    karar_guveni: 'YUKSEK',
    ana_ariza_tipi: 'PWF',
  },
  manuel_oncelik_override: false,
  override_nedeni: null,
  planlanan_baslangic_zamani: null,
  gercek_baslangic_zamani: null,
  tamamlanma_zamani: null,
  iptal_zamani: null,
  tamamlama_notu: null,
  iptal_nedeni: null,
  bekleme_nedeni: null,
  erp_ozeti: [
    {
      parca_kodu: 'PRC-001',
      parca_adi: 'Güç Rölesi',
      stok_durumu: 'MEVCUT',
      stok_yeterli: true,
      gerekli_miktar: 1,
    },
  ],
  olaylar: [
    {
      id: 1,
      olay_tipi: 'OLUSTURULDU',
      onceki_durum: null,
      yeni_durum: 'ACIK',
      onceki_genel_oncelik: null,
      yeni_genel_oncelik: null,
      gerceklestiren_kullanici_adi: 'ozge.06',
      detay: null,
      olusturulma_zamani: '2026-08-19T10:05:00Z',
    },
  ],
  guncellenme_zamani: '2026-08-19T10:05:00Z',
  tekrarlandi: false,
}

describe('IsEmriDetay', () => {
  it('iş emri detaylarını, atanan kullanıcıyı ve kaynak kararları sunar', async () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      kullanici: { id: 1, username: 'operator', rol: 'USER' },
      yukleniyor: false,
      giris: vi.fn(),
      cikis: vi.fn(),
    })
    vi.spyOn(isEmirleriApi, 'isEmriDetayiGetir').mockResolvedValue(MOCK_WO_DETAIL)

    render(
      <MemoryRouter initialEntries={['/app/is-emirleri/wo-101']}>
        <Routes>
          <Route path="/app/is-emirleri/:isEmriId" element={<IsEmriDetay />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('İş Emri WO-20260819-001')).toBeInTheDocument()
    })
    expect(screen.getByText('Pres Motoru Yüksek Sıcaklık Kontrolü')).toBeInTheDocument()
    expect(screen.getByText('ahmet.bakim')).toBeInTheDocument()
    expect(screen.getByText('Öncelik 5/5')).toBeInTheDocument()
    expect(screen.getByText('Kaynak Değerlendirmeyi Gör')).toBeInTheDocument()
  })

  it('ADMIN yalnız aktif kullanıcıya atar ve dönen güncel state bilgisini gösterir', async () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({ kullanici: { id: 1, username: 'admin', rol: 'ADMIN' }, yukleniyor: false, giris: vi.fn(), cikis: vi.fn() })
    vi.spyOn(isEmirleriApi, 'isEmriDetayiGetir').mockResolvedValue({ ...MOCK_WO_DETAIL, durum: 'ACIK', atanan_kullanici: null })
    vi.spyOn(yonetimApi, 'kullanicilariGetir').mockResolvedValue([
      { id: 5, username: 'aktif.user', email: '', rol: 'USER', is_active: true, date_joined: '' },
      { id: 6, username: 'pasif.user', email: '', rol: 'USER', is_active: false, date_joined: '' },
    ])
    const ata = vi.spyOn(isEmirleriApi, 'isEmriAta').mockResolvedValue({ ...MOCK_WO_DETAIL, version: 2, durum: 'ATANDI', atanan_kullanici: { id: 5, kullanici_adi: 'aktif.user' } })
    render(<MemoryRouter initialEntries={['/app/is-emirleri/wo-101']}><Routes><Route path="/app/is-emirleri/:isEmriId" element={<IsEmriDetay />} /></Routes></MemoryRouter>)
    fireEvent.click(await screen.findByRole('button', { name: 'Kullanıcı Ata' }))
    expect(await screen.findByRole('option', { name: 'aktif.user' })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: 'pasif.user' })).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Aktif kullanıcı'), { target: { value: '5' } })
    fireEvent.click(screen.getByRole('button', { name: 'Atamayı Kaydet' }))
    await waitFor(() => expect(ata).toHaveBeenCalledWith('wo-101', expect.objectContaining({ atanan_kullanici_id: 5, beklenen_version: 1 })))
    expect(await screen.findByText('aktif.user')).toBeInTheDocument()
  })

  it('atanmamış iş emrinde USER kontrollerini gizleyip nedenini açıklar', async () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({ kullanici: { id: 7, username: 'operator', rol: 'USER' }, yukleniyor: false, giris: vi.fn(), cikis: vi.fn() })
    vi.spyOn(isEmirleriApi, 'isEmriDetayiGetir').mockResolvedValue({ ...MOCK_WO_DETAIL, durum: 'ACIK', atanan_kullanici: null })
    render(<MemoryRouter initialEntries={['/app/is-emirleri/wo-101']}><Routes><Route path="/app/is-emirleri/:isEmriId" element={<IsEmriDetay />} /></Routes></MemoryRouter>)
    expect(await screen.findByText(/henüz atanmadı. Atama yapıldıktan sonra/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Kullanıcı Ata|Yeniden Ata/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Durum Geçişi Yap' })).not.toBeInTheDocument()
  })
})
