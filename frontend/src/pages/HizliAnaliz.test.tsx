import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { HizliAnaliz } from './HizliAnaliz'
import * as tahminApi from '../api/tahminler'
import type { RiskTahminiYaniti } from '../types/tahminler'
import { ApiHatasi } from '../types/apiHata'

afterEach(() => {
  vi.restoreAllMocks()
})

const MOCK_LOW_RISK_RESPONSE: RiskTahminiYaniti = {
  risk_orani: 0.12,
  risk_uyarisi: false,
  threshold: 0.229,
  model_version: 'binary-failure-1.0.0',
  pipeline_version: '1.0.0',
  ariza_tipi_degerlendirmesi: {
    durum: 'RISK_ESIK_ALTINDA',
    guvenilir_adaylar: [],
    deneysel_sinyaller: [],
    belirsiz_fiziksel_tip: false,
  },
}

const MOCK_HIGH_RISK_PWF_RESPONSE: RiskTahminiYaniti = {
  risk_orani: 0.7842,
  risk_uyarisi: true,
  threshold: 0.229,
  model_version: 'binary-failure-1.0.0',
  pipeline_version: '1.0.0',
  ariza_tipi_degerlendirmesi: {
    durum: 'DEGERLENDIRILDI',
    guvenilir_adaylar: [{ kod: 'PWF', olasilik: 0.91, threshold: 0.29 }],
    deneysel_sinyaller: [
      {
        kod: 'TWF',
        olasilik: 0.18,
        threshold: 0.05,
        esik_asildi: true,
        guven_durumu: 'YETERSIZ_DESTEK',
        operasyonel_kullanima_uygun: false,
      },
    ],
    belirsiz_fiziksel_tip: false,
  },
  aciklanabilirlik: {
    durum: 'ACIKLANDI',
    risk_aciklamasi: {
      target: 'Machine failure',
      output_space: 'probability',
      base_value: 0.1,
      ilk_etkiler: [
        {
          feature: 'mekanik_guc_w',
          gorunen_ad: 'Mekanik güç',
          original_feature_value: 4120.5,
          model_feature_value: 1.25,
          birim: 'W',
          shap_value: 0.35,
          yon: 'RISKI_ARTIRIR',
        },
      ],
    },
  },
}

const MOCK_UNCERTAIN_TYPE_RESPONSE: RiskTahminiYaniti = {
  risk_orani: 0.65,
  risk_uyarisi: true,
  threshold: 0.229,
  model_version: 'binary-failure-1.0.0',
  pipeline_version: '1.0.0',
  ariza_tipi_degerlendirmesi: {
    durum: 'DEGERLENDIRILDI',
    guvenilir_adaylar: [],
    deneysel_sinyaller: [],
    belirsiz_fiziksel_tip: true,
  },
}

describe('HizliAnaliz', () => {
  it('ilk açılışta %0 risk ve arıza mesajı göstermez, nötr placeholder gösterir', () => {
    render(<HizliAnaliz />)
    expect(screen.queryByText('%0')).not.toBeInTheDocument()
    expect(screen.queryByText('Bu ölçümde belirgin bir arıza sinyali görülmedi.')).not.toBeInTheDocument()
    expect(screen.getByText('Analiz sonucu burada görüntülenecek.')).toBeInTheDocument()
    expect(screen.getByText('Sensör ölçüm değerlerini girip analizi başlatın.')).toBeInTheDocument()
  })

  it('sensör giriş formunu ve varsayılan birimleri sunar', () => {
    render(<HizliAnaliz />)
    expect(screen.getByLabelText('Ürün Tipi')).toBeInTheDocument()
    expect(screen.getByLabelText('Hava Sıcaklığı')).toBeInTheDocument()
    expect(screen.getByLabelText('Proses Sıcaklığı')).toBeInTheDocument()
    expect(screen.getByLabelText('Dönüş Hızı')).toBeInTheDocument()
    expect(screen.getByLabelText('Tork')).toBeInTheDocument()
    expect(screen.getByLabelText('Takım Aşınması')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sensör Analizini Başlat' })).toBeInTheDocument()
  })

  it('düşük riskli analiz sonucunu ve mesajını doğru gösterir', async () => {
    vi.spyOn(tahminApi, 'hizliRiskTahmini').mockResolvedValue(MOCK_LOW_RISK_RESPONSE)
    render(<HizliAnaliz />)

    await userEvent.click(screen.getByRole('button', { name: 'Sensör Analizini Başlat' }))

    await waitFor(() => {
      expect(screen.getByText('%12')).toBeInTheDocument()
      expect(screen.getByText('Bu ölçümde belirgin bir arıza sinyali görülmedi.')).toBeInTheDocument()
    })
  })

  it('yüksek riskli analizi, güvenilir aday PWF, TWF uyarısını ve SHAP görünümünü sunar', async () => {
    vi.spyOn(tahminApi, 'hizliRiskTahmini').mockResolvedValue(MOCK_HIGH_RISK_PWF_RESPONSE)
    render(<HizliAnaliz />)

    await userEvent.click(screen.getByRole('button', { name: 'Sensör Analizini Başlat' }))

    await waitFor(() => {
      expect(screen.getByText('%78')).toBeInTheDocument()
      expect(screen.getByText('Bu ölçüm bakım açısından incelenmeli.')).toBeInTheDocument()
    })

    expect(screen.getByText('Güç kaynaklı sorun (PWF)')).toBeInTheDocument()
    expect(screen.getByText(/Takım aşınması sinyali algılandı/)).toBeInTheDocument()

    // SHAP kullanıcı dostu metinleri
    expect(screen.getByText('Riski Etkileyen Başlıca Değerler')).toBeInTheDocument()
    expect(screen.getByText('Mekanik güç')).toBeInTheDocument()
    expect(screen.getByText('Riski artırıyor')).toBeInTheDocument()

    // Raw technical names should NOT be present in primary feature card
    expect(screen.queryByText('mekanik_guc_w')).not.toBeInTheDocument()
    expect(screen.queryByText('model_feature_value')).not.toBeInTheDocument()
  })

  it('teknik detaylar alanı varsayılan olarak kapalıdır ve kullanıcı açtığında görünür', async () => {
    vi.spyOn(tahminApi, 'hizliRiskTahmini').mockResolvedValue(MOCK_LOW_RISK_RESPONSE)
    render(<HizliAnaliz />)

    await userEvent.click(screen.getByRole('button', { name: 'Sensör Analizini Başlat' }))
    await waitFor(() => expect(screen.getByText('%12')).toBeInTheDocument())

    // Default state: technical details hidden
    expect(screen.queryByText(/binary-failure-1.0.0/)).not.toBeInTheDocument()

    // Click to open accordion
    await userEvent.click(screen.getByRole('button', { name: /Teknik Detaylar/ }))
    expect(screen.getByText(/binary-failure-1.0.0/)).toBeInTheDocument()
  })

  it('belirsiz fiziksel tip durumunda açıklayıcı mesaj verir', async () => {
    vi.spyOn(tahminApi, 'hizliRiskTahmini').mockResolvedValue(MOCK_UNCERTAIN_TYPE_RESPONSE)
    render(<HizliAnaliz />)

    await userEvent.click(screen.getByRole('button', { name: 'Sensör Analizini Başlat' }))

    await waitFor(() => {
      expect(screen.getByText(/güvenilir bir fiziksel arıza tipi belirlenemedi/)).toBeInTheDocument()
    })
  })

  it('400 alan hatalarını ve 503 servis hatalarını kullanıcı dostu gösterir', async () => {
    vi.spyOn(tahminApi, 'hizliRiskTahmini').mockRejectedValue(
      new ApiHatasi(400, 'GECERSIZ_ISTEK', 'Gönderilen bilgilerde hatalar var.', {
        hava_sicakligi_k: ['Hava sıcaklığı 0 K’den büyük olmalıdır.'],
      })
    )

    render(<HizliAnaliz />)
    await userEvent.click(screen.getByRole('button', { name: 'Sensör Analizini Başlat' }))

    await waitFor(() => {
      expect(screen.getByText('Hava sıcaklığı 0 K’den büyük olmalıdır.')).toBeInTheDocument()
    })
  })

  it('submit sırasında tekrar tıklamayı ve duplicate isteği engeller', async () => {
    let resolvePrediction: (val: RiskTahminiYaniti) => void = () => {}
    const predictionPromise = new Promise<RiskTahminiYaniti>((res) => {
      resolvePrediction = res
    })

    vi.spyOn(tahminApi, 'hizliRiskTahmini').mockReturnValue(predictionPromise)

    render(<HizliAnaliz />)
    const btn = screen.getByRole('button', { name: 'Sensör Analizini Başlat' })
    await userEvent.click(btn)

    expect(btn).toBeDisabled()
    expect(screen.getByText('Sensör Analizi Yapılıyor…')).toBeInTheDocument()

    resolvePrediction(MOCK_LOW_RISK_RESPONSE)
    await waitFor(() => expect(btn).not.toBeDisabled())
  })
})
