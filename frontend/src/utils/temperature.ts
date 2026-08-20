const MUTLAK_SIFIR_C = -273.15

export function celsiusToKelvin(celsius: number): number {
  if (!Number.isFinite(celsius) || celsius < MUTLAK_SIFIR_C) {
    throw new RangeError('Sıcaklık mutlak sıfırın altında veya geçersiz olamaz.')
  }
  return celsius + 273.15
}

export function kelvinToCelsius(kelvin: number): number {
  if (!Number.isFinite(kelvin) || kelvin < 0) {
    throw new RangeError('Kelvin değeri negatif veya geçersiz olamaz.')
  }
  return kelvin - 273.15
}
