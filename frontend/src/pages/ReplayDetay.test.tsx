import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ReplayDetay } from './ReplayDetay'
import * as replayApi from '../api/replay'
import * as authContext from '../app/AuthContext'
import type { ReplayOturumDetay } from '../types/replay'

afterEach(() => {
  vi.restoreAllMocks()
})

const MOCK_REPLAY_DETAIL: ReplayOturumDetay = {
  id: 'rep-101',
  makine: { id: 1, kod: 'M-101', ad: 'Pres Motoru 1' },
  split: 'test' as const,
  durum: 'TAMAMLANDI' as const,
  baslangic_ofseti: 0,
  toplam_oge: 250,
  varsayilan_batch_boyutu: 5,
  sanal_aralik_saniye: 60,
  baslatilma_zamani: '2026-08-19T10:00:00Z',
  tamamlanma_zamani: null,
  iptal_zamani: null,
  hata_mesaji: null,
  ilerleme: {
    bekleyen: 245,
    isleniyor: 0,
    basarili: 5,
    basarisiz: 0,
    atlandi: 0,
    tamamlanma_yuzdesi: 2,
  },
  olusturulma_zamani: '2026-08-19T09:55:00Z',
  version: 2,
  metrikler: {
    degerlendirilen_oge_sayisi: 5,
    binary: {
      precision: 0.8,
      recall: 0.9,
      f1: 0.847,
      pr_auc: 0.92,
      support: 1,
      predicted_positive: 1,
      confusion_matrix: {
        true_negative: 4,
        false_positive: 1,
        false_negative: 2,
        true_positive: 3,
      },
    },
    failure_types: {},
    rnf_ground_truth_count: 0,
    metrik_uyarilari: [],
  },
  olaylar: [],
  son_ogeler: [
    {
      id: 1,
      sira: 1,
      external_machine_id: 'M-101',
      durum: 'BASARILI',
      tahmin_kaydi_id: 'pred-101',
      hata_mesaji: null,
      tamamlanma_zamani: '2026-08-19T10:00:05Z',
      risk_uyarisi: true,
      oncelik_seviyesi: 'KRITIK',
    },
  ],
}

describe('ReplayDetay', () => {
  it('replay detaylarını, performans metriklerini ve işlenen öğeleri sunar', async () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      kullanici: { id: 1, username: 'admin', rol: 'ADMIN' },
      yukleniyor: false,
      giris: vi.fn(),
      cikis: vi.fn(),
    })
    vi.spyOn(replayApi, 'replayOturumuDetayiGetir').mockResolvedValue(MOCK_REPLAY_DETAIL)
    vi.spyOn(replayApi, 'replayOgeleriniGetir').mockResolvedValue({ count: 1, next: null, previous: null, results: MOCK_REPLAY_DETAIL.son_ogeler })

    render(
      <MemoryRouter initialEntries={['/app/replay/rep-101']}>
        <Routes>
          <Route path="/app/replay/:sessionId" element={<ReplayDetay />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Pres Motoru 1 Replay Oturumu')).toBeInTheDocument()
    })
    expect(screen.getByText('Tamamlandı')).toBeInTheDocument()
    expect(screen.queryByText(/Accuracy|Model Doğruluğu/i)).not.toBeInTheDocument()
    expect(screen.getByText('Precision')).toBeInTheDocument()
    expect(screen.getByText('%80,0')).toBeInTheDocument()
    expect(screen.getByText('Recall')).toBeInTheDocument()
    expect(screen.getByText('%90,0')).toBeInTheDocument()
    expect(screen.getByText('PR-AUC')).toBeInTheDocument()
    expect(screen.getByText('%92,0')).toBeInTheDocument()
    expect(screen.getByText('F1-Skoru (Yardımcı)')).toBeInTheDocument()
    expect(screen.getByText('Confusion Matrix')).toBeInTheDocument()
    expect(screen.getByText('TN — Doğru sağlam')).toBeInTheDocument()
    expect(screen.getByText('FP — Yanlış alarm')).toBeInTheDocument()
    expect(screen.getByText('FN — Kaçırılan arıza')).toBeInTheDocument()
    expect(screen.getByText('TP — Doğru arıza')).toBeInTheDocument()
    expect(screen.getByText('Değerlendirmeyi Gör')).toBeInTheDocument()
  })

  it('PR-AUC unavailable uyarısını güvenli biçimde gösterir', async () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      kullanici: { id: 2, username: 'user', rol: 'USER' },
      yukleniyor: false,
      giris: vi.fn(),
      cikis: vi.fn(),
    })
    vi.spyOn(replayApi, 'replayOturumuDetayiGetir').mockResolvedValue({
      ...MOCK_REPLAY_DETAIL,
      metrikler: {
        ...MOCK_REPLAY_DETAIL.metrikler,
        binary: { ...MOCK_REPLAY_DETAIL.metrikler.binary!, pr_auc: null },
        metrik_uyarilari: ['PR-AUC hesaplanamadı: replay içinde gerçek pozitif arıza örneği yok.'],
      },
    })
    vi.spyOn(replayApi, 'replayOgeleriniGetir').mockResolvedValue({ count: 0, next: null, previous: null, results: [] })

    render(
      <MemoryRouter initialEntries={['/app/replay/rep-101']}>
        <Routes><Route path="/app/replay/:sessionId" element={<ReplayDetay />} /></Routes>
      </MemoryRouter>
    )

    expect(await screen.findByText('Hesaplanamadı')).toBeInTheDocument()
    expect(screen.getByText(/gerçek pozitif arıza örneği yok/i)).toBeInTheDocument()
    expect(screen.queryByText(/NaN|Infinity/)).not.toBeInTheDocument()
  })
})
