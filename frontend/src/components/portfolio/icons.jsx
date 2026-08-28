const base = { fill: "none", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round" };

export function IconCompareColumns({ size = 13 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" stroke="currentColor" {...base}>
      <rect x="4" y="3" width="6" height="18" rx="1.5" />
      <rect x="14" y="3" width="6" height="18" rx="1.5" />
    </svg>
  );
}

export function IconPlus({ size = 13 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" stroke="currentColor" {...base}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function IconPencil({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" stroke="currentColor" {...base}>
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </svg>
  );
}