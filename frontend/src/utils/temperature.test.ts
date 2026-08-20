import { describe, expect, it } from 'vitest'

import { celsiusToKelvin, kelvinToCelsius } from './temperature'

describe('temperature conversions', () => {
  it('converts Celsius and Kelvin without rounding the payload', () => {
    expect(celsiusToKelvin(25)).toBe(298.15)
    expect(kelvinToCelsius(298.15)).toBe(25)
  })

  it('rejects non-finite and below-absolute-zero values', () => {
    expect(() => celsiusToKelvin(-273.16)).toThrow(RangeError)
    expect(() => celsiusToKelvin(Number.NaN)).toThrow(RangeError)
    expect(() => kelvinToCelsius(-0.01)).toThrow(RangeError)
  })
})
