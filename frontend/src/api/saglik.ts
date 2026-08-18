import type { SaglikYaniti } from '../types/saglik'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export async function saglikDurumunuGetir(): Promise<SaglikYaniti> {
  const response = await fetch(`${API_BASE_URL}/api/saglik/`)
  if (!response.ok) {
    throw new Error('Backend sağlık kontrolü başarısız oldu.')
  }
  return response.json() as Promise<SaglikYaniti>
}
