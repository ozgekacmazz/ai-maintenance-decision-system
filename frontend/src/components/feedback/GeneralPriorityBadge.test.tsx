import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { GeneralPriorityBadge } from './GeneralPriorityBadge'

describe('GeneralPriorityBadge', () => {
  it.each([1, 2, 3, 4, 5] as const)('öncelik %s için sayısal /5 metni gösterir', (priority) => {
    render(<GeneralPriorityBadge genelOncelik={priority} />)

    expect(screen.getByText(`Öncelik ${priority}/5`)).toBeInTheDocument()
  })

  it('canonical değer yoksa legacy önceliği açıkça işaretler', () => {
    render(<GeneralPriorityBadge genelOncelik={null} legacyOncelik="KRITIK" />)

    expect(screen.getByText('Kritik')).toBeInTheDocument()
    expect(screen.getByText('Legacy öncelik')).toBeInTheDocument()
  })
})
