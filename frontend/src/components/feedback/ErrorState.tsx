interface ErrorStateProps {
  mesaj: string
  traceId?: string | null
  onRetry?: () => void
}

export function ErrorState({ mesaj, traceId, onRetry }: ErrorStateProps) {
  return (
    <div className="hata" role="alert" style={{ textAlign: 'center', padding: '24px' }}>
      <p style={{ margin: 0, fontWeight: 600 }}>{mesaj}</p>
      {traceId && (
        <p style={{ margin: '8px 0 0 0', fontSize: '0.8rem', opacity: 0.8 }}>
          Takip kodu: {traceId}
        </p>
      )}
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          style={{ width: 'auto', marginTop: '16px', marginInline: 'auto' }}
        >
          Tekrar dene
        </button>
      )}
    </div>
  )
}
