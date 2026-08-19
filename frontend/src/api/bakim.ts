import { kimlikliIstek } from './auth'
import { responseHatasiniNormalizeEt } from '../types/apiHata'
import type { MakineOzet, SayfalanmisYanit } from '../types/tahminler'

export async function makineleriGetir(): Promise<SayfalanmisYanit<MakineOzet>> {
  const response = await kimlikliIstek('/api/makine-secenekleri/')

  if (!response.ok) {
    throw await responseHatasiniNormalizeEt(response)
  }

  return response.json() as Promise<SayfalanmisYanit<MakineOzet>>
}
