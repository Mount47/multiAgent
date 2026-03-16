import { useEffect, useState } from 'react'
import { fetchProviders, fetchDefaultProvider } from '../api/client'
import type { ProviderItem } from '../types/api'

export function useProviders() {
  const [providers, setProviders] = useState<ProviderItem[]>([])
  const [defaultProvider, setDefaultProvider] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([fetchProviders(), fetchDefaultProvider()])
      .then(([list, def]) => {
        setProviders(list)
        setDefaultProvider(def.default_provider || (list[0]?.name ?? ''))
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return { providers, defaultProvider, loading }
}
