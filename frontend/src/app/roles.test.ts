import { describe, expect, it } from 'vitest'
import { adminMi } from './roles'
import type { KullaniciOzeti } from '../types/auth'

describe('adminMi', () => {
  it('yalnız gerçek ADMIN rolünü kabul eder', () => {
    expect(adminMi({ rol: 'ADMIN' })).toBe(true)
    expect(adminMi({ rol: 'USER' })).toBe(false)
  })

  it('null, undefined ve eksik rolü güvenli biçimde reddeder', () => {
    expect(adminMi(null)).toBe(false)
    expect(adminMi(undefined)).toBe(false)
    expect(adminMi({} as Pick<KullaniciOzeti, 'rol'>)).toBe(false)
  })
})
