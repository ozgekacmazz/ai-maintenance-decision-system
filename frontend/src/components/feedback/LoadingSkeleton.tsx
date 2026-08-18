export function LoadingSkeleton({ adet = 3 }: { adet?: number }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }} role="status" aria-label="Veriler yükleniyor">
      {Array.from({ length: adet }).map((_, i) => (
        <div
          key={i}
          className="skeleton"
          style={{ height: '72px', width: '100%' }}
        />
      ))}
      <span className="sr-only" style={{ position: 'absolute', width: '1px', height: '1px', overflow: 'hidden' }}>
        Yükleniyor…
      </span>
    </div>
  )
}
