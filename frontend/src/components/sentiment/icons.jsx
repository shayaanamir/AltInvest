const base = { fill: "none", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round" };

export function IconStar({ size = 15, filled = false }) {
  if (filled) {
    return (
      <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} fill="currentColor" className="bi bi-star-fill" viewBox="0 0 16 16">
        <path d="M3.612 15.443c-.386.198-.824-.149-.746-.592l.83-4.73L.173 6.765c-.329-.314-.158-.888.283-.95l4.898-.696L7.538.792c.197-.39.73-.39.927 0l2.184 4.327 4.898.696c.441.062.612.636.282.95l-3.522 3.356.83 4.73c.078.443-.36.79-.746.592L8 13.187l-4.389 2.256z"/>
      </svg>
    );
  }
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2.5l2.9 6.4 6.9.7-5.2 4.7 1.5 6.9L12 17.6l-6.1 3.6 1.5-6.9-5.2-4.7 6.9-.7z" />
    </svg>
  );
}

export function IconBell({ size = 15 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" stroke="currentColor" {...base}>
      <path d="M18 8a6 6 0 10-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.7 21a2 2 0 01-3.4 0" />
    </svg>
  );
}

export function IconFolder({ size = 15 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" stroke="currentColor" {...base}>
      <path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
    </svg>
  );
}

export function IconChevronDown({ size = 13 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" stroke="currentColor" {...base}>
      <path d="M6 9l6 6 6-6" />
    </svg>
  );
}

export function IconArrowUpRight({ size = 13 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" stroke="currentColor" {...base}>
      <path d="M7 17L17 7M9 7h8v8" />
    </svg>
  );
}

export function IconArrowDownRight({ size = 13 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" stroke="currentColor" {...base}>
      <path d="M7 7l10 10M17 7v10H7" />
    </svg>
  );
}

export function IconArrowRight({ size = 13 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" stroke="currentColor" {...base}>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}

export function IconExternal({ size = 12 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" stroke="currentColor" {...base}>
      <path d="M7 17L17 7M8 7h9v9" />
    </svg>
  );
}

export function IconTrash({ size = 14 }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-trash" viewBox="0 0 16 16">
      <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0z"/>
      <path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4zM2.5 3h11V2h-11z"/>
    </svg>
  );
}

export function IconSearch({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" stroke="currentColor" {...base}>
      <circle cx="11" cy="11" r="7" />
      <path d="M21 21l-4.35-4.35" />
    </svg>
  );
}

export function IconRefresh({ size = 13 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" stroke="currentColor" {...base}>
      <path d="M4 4v6h6M20 20v-6h-6" />
      <path d="M4.5 15a8 8 0 0014.9 2.5M19.5 9A8 8 0 004.6 6.5" />
    </svg>
  );
}

export function IconInfo({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" stroke="currentColor" {...base}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5M12 8h.01" />
    </svg>
  );
}

export function IconListView({ size = 15 }) {
  return (
    <svg width={size} height={size} fill="currentColor" className="bi bi-list-ul" viewBox="0 0 16 16">
      <path fillRule="evenodd" d="M5 11.5a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5m0-4a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5m0-4a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5m-3 1a1 1 0 1 0 0-2 1 1 0 0 0 0 2m0 4a1 1 0 1 0 0-2 1 1 0 0 0 0 2m0 4a1 1 0 1 0 0-2 1 1 0 0 0 0 2"/>
    </svg>
  );
}

export function IconGrid2({ size = 15 }) {
  return (
    <svg width={size} height={size} fill="currentColor" className="bi bi-grid" viewBox="0 0 16 16">
      <path d="M1 2.5A1.5 1.5 0 0 1 2.5 1h3A1.5 1.5 0 0 1 7 2.5v3A1.5 1.5 0 0 1 5.5 7h-3A1.5 1.5 0 0 1 1 5.5zM2.5 2a.5.5 0 0 0-.5.5v3a.5.5 0 0 0 .5.5h3a.5.5 0 0 0 .5-.5v-3a.5.5 0 0 0-.5-.5zm6.5.5A1.5 1.5 0 0 1 10.5 1h3A1.5 1.5 0 0 1 15 2.5v3A1.5 1.5 0 0 1 13.5 7h-3A1.5 1.5 0 0 1 9 5.5zm1.5-.5a.5.5 0 0 0-.5.5v3a.5.5 0 0 0 .5.5h3a.5.5 0 0 0 .5-.5v-3a.5.5 0 0 0-.5-.5zM1 10.5A1.5 1.5 0 0 1 2.5 9h3A1.5 1.5 0 0 1 7 10.5v3A1.5 1.5 0 0 1 5.5 15h-3A1.5 1.5 0 0 1 1 13.5zm1.5-.5a.5.5 0 0 0-.5.5v3a.5.5 0 0 0 .5.5h3a.5.5 0 0 0 .5-.5v-3a.5.5 0 0 0-.5-.5zm6.5.5A1.5 1.5 0 0 1 10.5 9h3a1.5 1.5 0 0 1 1.5 1.5v3a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 9 13.5zm1.5-.5a.5.5 0 0 0-.5.5v3a.5.5 0 0 0 .5.5h3a.5.5 0 0 0 .5-.5v-3a.5.5 0 0 0-.5-.5z"/>
    </svg>
  );
}