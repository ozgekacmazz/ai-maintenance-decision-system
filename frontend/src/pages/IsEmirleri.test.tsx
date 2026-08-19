import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { IsEmirleri } from './IsEmirleri'
import * as isEmirleriApi from '../api/isEmirleri'
import * as bakimApi from '../api/bakim'
import * as authContext from '../app/AuthContext'

afterEach(() => {
  vi.restoreAllMocks()
})

const MOCK_LIST = {
  count: 1,
  next: null,
  previous: null,
  results: [
    {
      id: 'wo-101',
      is_emri_numarasi: 'WO-20260819-001',
      makine: { id: 1, kod: 'M-101', ad: 'Pres Motoru 1' },
      ana_aksiyon: 'ACIL_TEKNIK_DEGERLENDIRME',
      erp_ozeti: [
        { parca_kodu: 'PRC-001', parca_adi: 'Güç Rölesi', stok_durumu: 'MEVCUT', stok_yeterli: true, gerekli_miktar: 2 },
        { parca_kodu: 'PRC-002', parca_adi: 'Sigorta', stok_durumu: 'MEVCUT', stok_yeterli: true, gerekli_miktar: 1 },
        { parca_kodu: 'PRC-003', parca_adi: 'Kablo', stok_durumu: 'MEVCUT', stok_yeterli: true, gerekli_miktar: 1 },
      ],
      durum: 'ACIK' as const,
      etkin_oncelik_seviyesi: 'KRITIK' as const,
      kaynak_oncelik_seviyesi: 'KRITIK' as const,
      kaynak_genel_oncelik: 5 as const,
      kaynak_genel_oncelik_formul_surumu: 'general-priority-1.0.0',
      etkin_genel_oncelik: 5 as const,
      atanan_kullanici: null,
      hedef_mudahale_zamani: '2026-08-19T14:00:00Z',
      gecikmis: false,
      olcum_zamani: '2026-08-19T10:00:00Z',
      olusturan: { id: 2, kullanici_adi: 'ozge.06' },
      olusturulma_zamani: '2026-08-19T10:05:00Z',
      version: 1,
    },
  ],
}

describe('IsEmirleri', () => {
  it('iş emirleri listesini ve filtrelerini doğru görüntüler', async () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      kullanici: { id: 1, username: 'operator', rol: 'USER' },
      yukleniyor: false,
      giris: vi.fn(),
      cikis: vi.fn(),
    })
    vi.spyOn(bakimApi, 'makineleriGetir').mockResolvedValue({ count: 0, next: null, previous: null, results: [] })
    vi.spyOn(isEmirleriApi, 'isEmirleriniGetir').mockResolvedValue(MOCK_LIST)

    render(
      <MemoryRouter>
        <IsEmirleri />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('WO-20260819-001')).toBeInTheDocument()
    })
    expect(screen.getByText('Pres Motoru 1')).toBeInTheDocument()
    expect(screen.getAllByText('Öncelik 5/5').length).toBeGreaterThan(0)
    expect(screen.getByText('Acil teknik değerlendirme')).toBeInTheDocument()
    expect(screen.getByText('Güç Rölesi ×2, Sigorta ×1 +1 parça')).toBeInTheDocument()
    expect(screen.getAllByText('Açık').length).toBeGreaterThan(0)
  })

  it('eksik aksiyon ve parça verisini kullanıcı dostu boş durumlarla gösterir', async () => {
    vi.spyOn(bakimApi, 'makineleriGetir').mockResolvedValue({ count: 0, next: null, previous: null, results: [] })
    vi.spyOn(isEmirleriApi, 'isEmirleriniGetir').mockResolvedValue({
      ...MOCK_LIST,
      results: [{ ...MOCK_LIST.results[0], ana_aksiyon: null, erp_ozeti: [] }],
    })

    render(<MemoryRouter><IsEmirleri /></MemoryRouter>)

    expect(await screen.findByText('Aksiyon belirtilmemiş')).toBeInTheDocument()
    expect(screen.getByText('Parça önerisi yok')).toBeInTheDocument()
  })
})
