/**
 * Returns a flat style map keyed by component/element name,
 * derived from the current theme tokens object `t`.
 */
export function makeStyles(t) {
  return {
    // ── Root layout ──────────────────────────────────────────
    root: {
      display: "flex",
      height: "100vh",
      width: "100vw",
      background: t.bgBase,
      fontFamily: "'DM Sans','Segoe UI',sans-serif",
      color: t.textPrimary,
      overflow: "hidden",
      transition: "background 0.25s, color 0.25s",
    },

    // ── Sidebar ───────────────────────────────────────────────
    sidebar: {
      width: 220,
      minWidth: 220,
      background: t.bgSidebar,
      borderRight: `1px solid ${t.border}`,
      display: "flex",
      flexDirection: "column",
      padding: "16px 0 12px",
      transition: "width 0.3s ease, min-width 0.3s ease, background 0.25s, border-color 0.25s",
    },
    logo: {
      display: "flex",
      alignItems: "center",
      gap: 7,
      padding: "0 14px 14px",
      borderBottom: `1px solid ${t.border}`,
    },
    logoIcon: {
      width: 28, height: 28,
      background: t.bgCard2,
      borderRadius: 7,
      display: "flex", alignItems: "center", justifyContent: "center",
    },
    logoText: { fontWeight: 700, fontSize: 14, color: t.textPrimary, letterSpacing: "-0.3px" },
    menuLabel: {
      fontSize: 9.5, fontWeight: 600, color: t.textMuted,
      letterSpacing: "0.08em", textTransform: "uppercase",
      padding: "12px 14px 5px",
    },
    nav: { display: "flex", flexDirection: "column", gap: 3, padding: "0 10px" },
    navItem: {
      display: "flex", alignItems: "center", gap: 10,
      padding: "9px 12px", borderRadius: 8, cursor: "pointer",
      fontSize: 13.5, color: t.textSecondary,
      transition: "background 0.15s, color 0.15s, justify-content 0.3s ease",
    },
    navItemActive: {
      background: t.navActiveBg, color: t.textPrimary, fontWeight: 600,
    },
    navIcon:  { fontSize: 15, width: 20, textAlign: "center", opacity: 0.8 },
    navLabel: { fontSize: 13.5, fontWeight: 500, whiteSpace: "nowrap" },
    badge: {
      fontSize: 8, fontWeight: 700, padding: "1px 5px", borderRadius: 4,
      background: t.badgeNewBg, color: t.badgeNewText, letterSpacing: "0.04em",
    },
    proBox: {
      margin: "0 8px 10px",
      background: t.proBg, borderRadius: 8, padding: 10,
      border: `1px solid ${t.border}`,
    },
    proAvatar: {
      width: 24, height: 24, borderRadius: "50%",
      background: t.navActiveBg,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: 10, color: t.proText,
      border: `1.5px solid ${t.navActiveBorder}`,
    },
    proTitle: { fontSize: 10.5, fontWeight: 700, color: t.proText },
    proSub:   { fontSize: 9, color: t.textMuted, marginTop: 1, lineHeight: 1.3 },
    bottomNav: {
      display: "flex", flexDirection: "column", gap: 1,
      padding: "8px 6px 0", borderTop: `1px solid ${t.border}`, marginTop: 4,
    },

    // ── Topbar ────────────────────────────────────────────────
    topbar: {
      height: 58,
      background: t.topbarBg,
      borderBottom: `1px solid ${t.border}`,
      display: "flex", alignItems: "center",
      padding: "0px 40px 0 40px", gap: 14, flexShrink: 0,
      transition: "background 0.25s, border-color 0.25s",
    },
    searchBox: {
      flex: 1, background: t.searchBg,
      border: `1px solid ${t.borderLight}`, borderRadius: 8, height: 34,
      display: "flex", alignItems: "center", padding: "0 10px", gap: 7,
      maxWidth: 380,
    },
    searchPlaceholder: { fontSize: 11.5, color: t.textMuted, flex: 1 },
    kbd: {
      fontSize: 10, color: t.textMuted,
      background: t.bgCard2, border: `1px solid ${t.borderLight}`,
      borderRadius: 4, padding: "1px 5px", fontFamily: "monospace",
    },
    marketStatus: {
      display: "flex", alignItems: "center", gap: 5,
      background: t.bgCard2, border: `1px solid ${t.borderLight}`,
      borderRadius: 20, padding: "4px 10px",
    },
    marketDot: {
      width: 6, height: 6, borderRadius: "50%",
      background: t.accentGreen, boxShadow: `0 0 5px ${t.accentGreen}`,
    },
    marketLabel: { fontSize: 11, color: t.textSecondary, fontWeight: 500 },
    notifBtn: { background: "none", border: "none", cursor: "pointer", fontSize: 15, color: t.textSecondary, padding: 4 },
    themeToggle: { background: "none", border: "none", cursor: "pointer", padding: 0 },
    themeToggleTrack: {
      width: 50, height: 24,
      background: t.bgCard2, border: `1px solid ${t.borderLight}`,
      borderRadius: 25, position: "relative", padding: 2,
      display: "flex", alignItems: "center",
    },
    themeToggleThumb: {
      width: 20, height: 20, borderRadius: "50%",
      background: t.navActiveBg, border: `1px solid ${t.borderLight}`,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: 11, transition: "transform 0.25s cubic-bezier(0.34,1.56,0.64,1)",
    },
    userInfo:  { display: "flex", alignItems: "center", gap: 8 },
    userName:  { fontSize: 11.5, fontWeight: 600, color: t.textPrimary, textAlign: "right" },
    userTier:  { fontSize: 9.5, color: t.textSecondary, textAlign: "right" },
    avatar: {
      width: 32, height: 32, borderRadius: "50%",
      background: "linear-gradient(135deg,#4b8dff,#4b8dff)",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: 11, fontWeight: 700, color: "#fff",
    },

    // ── Page layout ───────────────────────────────────────────
    main:    { flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", background: t.bgBase, transition: "background 0.25s" },
    content: { flex: 1, overflow: "auto", padding: "40px 40px 20px" },
    pageHeader: { display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 0, paddingBottom: "40px" },
    pageTitle:  { fontSize: 30, fontWeight: 700, color: t.textPrimary, letterSpacing: "-0.5px", margin: 0 },
    pageSub:    { fontSize: 13, color: t.textSecondary, margin: 0, marginTop: 4 },
    pageActions:{ display: "flex", alignItems: "center", gap: 8 },
    btnOutline: {
      background: "none", border: `1px solid ${t.btnOutlineBorder}`,
      borderRadius: 8, padding: "10px 17px", fontSize: 14,
      color: t.btnOutlineText, cursor: "pointer", fontWeight: 500,
    },
    btnPrimary: {
      background: t.btnPrimaryBg, border: "none", borderRadius: 8,
      padding: "10  px 17px", fontSize: 14, color: "#fff",
      cursor: "pointer", fontWeight: 600,
    },

    // ── Stats row (dashboard) ─────────────────────────────────
    statsRow: { display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1.15fr", gap: 10, marginBottom: 12 },
    statCard: {
      background: t.bgCard, border: `1px solid ${t.border}`,
      borderRadius: 10, padding: "13px 15px 14px",
      transition: "background 0.25s, border-color 0.25s",
    },
    statLabel: { fontSize: 10.5, color: t.textSecondary, marginBottom: 5, fontWeight: 500 },
    statBadge: { fontSize: 10, fontWeight: 700, padding: "2px 7px", borderRadius: 20, display: "inline-block", marginBottom: 8 },
    statValue: { fontSize: 24, fontWeight: 700, color: t.textPrimary, letterSpacing: "-0.5px" },
    moodLabel: { fontSize: 10.5, color: t.textSecondary, marginBottom: 8, fontWeight: 500 },
    moodValue: { display: "flex", alignItems: "center", justifyContent: "space-between" },
    moodSquare:{ width: 28, height: 28, borderRadius: 5, background: "linear-gradient(135deg,#4b8dff,#00c9b0)", opacity: 0.85 },
    moodConf:  { fontSize: 10, color: t.textMuted, marginTop: 5 },

    // ── Charts row (dashboard) ────────────────────────────────
    chartsRow:   { display: "grid", gridTemplateColumns: "1fr 288px", gap: 10, marginBottom: 12 },
    card: {
      background: t.bgCard, border: `1px solid ${t.border}`,
      borderRadius: 10, overflow: "hidden",
      transition: "background 0.25s, border-color 0.25s",
    },
    cardHeader: {
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "18px 14px 18px", borderBottom: `1px solid ${t.border}`,
    },
    cardTitle:   { fontSize: 17, fontWeight: 700, color: t.textPrimary },
    timeFilters: { display: "flex", gap: 2, background: t.bgCard2, borderRadius: 7, padding: 2 },
    timeBtn:     { background: "none", border: "none", borderRadius: 5, padding: "3px 7px", fontSize: 10.5, color: t.textMuted, cursor: "pointer", fontWeight: 500 },
    timeBtnActive:{ background: t.bgHover, color: t.textPrimary, fontWeight: 700 },
    viewAllBtn:  { background: "none", border: "none", fontSize: 11, color: t.accentBlue, cursor: "pointer", fontWeight: 600 },

    // ── Insights ──────────────────────────────────────────────
    insightItem: { padding: "16px 18px", borderBottom: `1px solid ${t.border}` },
    insightMeta: { display: "flex", justifyContent: "space-between", marginBottom: 8 },
    insightSrc:  { fontSize: 10, fontWeight: 700, color: t.textMuted, background: t.bgCard2, padding: "2px 8px", borderRadius: 4, border: `1px solid ${t.borderLight}` },
    insightTime: { fontSize: 10, color: t.textMuted },
    insightHL:   { fontSize: 13, color: t.textPrimary, fontWeight: 500, lineHeight: 1.5, marginBottom: 8 },

    // ── Trending assets ───────────────────────────────────────
    trendingHdr: { display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 14px 10px", borderBottom: `1px solid ${t.border}` },
    assetGrid:   { display: "grid", gridTemplateColumns: "repeat(4,1fr)" },
    assetCard:   { padding: "12px 14px", borderRight: `1px solid ${t.border}` },
    assetTop:    { display: "flex", alignItems: "flex-start", gap: 8 },
    assetSym: {
      background: t.bgCard2, border: `1px solid ${t.borderLight}`,
      borderRadius: 6, fontSize: 9, fontWeight: 800, color: t.textPrimary,
      padding: "3px 6px", letterSpacing: "0.02em", whiteSpace: "nowrap",
    },
    assetName:  { fontSize: 11.5, fontWeight: 700, color: t.textPrimary },
    assetCat:   { fontSize: 9.5, color: t.textMuted, marginTop: 1 },
    assetPb:    { textAlign: "right", marginLeft: "auto" },
    assetPrice: { fontSize: 12, fontWeight: 700, color: t.textPrimary },
    assetChg:   { fontSize: 10, fontWeight: 600, marginTop: 1 },
    assetFooter:{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 4 },
    scoreRow:   { display: "flex", alignItems: "center", gap: 4 },
    scoreIcon:  { fontSize: 11, color: t.accentBlue },
    scoreLbl:   { fontSize: 10, color: t.textMuted },
    assetSig:   { fontSize: 10.5, fontWeight: 700 },

    // ── Portfolio page ────────────────────────────────────────
    portfolioStatsRow: {
      display: "grid",
      gridTemplateColumns: "1fr 1fr 1fr",
      gap: 10,
      marginBottom: 12,
    },
    portfolioChartsRow: {
      display: "grid",
      gridTemplateColumns: "1fr 260px",
      gap: 10,
      marginBottom: 12,
    },
    diversificationRing: {
      position: "relative",
      width: 64, height: 64,
      display: "flex", alignItems: "center", justifyContent: "center",
      flexShrink: 0,
    },
    diversificationRingLabel: {
      position: "absolute",
      fontSize: 11, fontWeight: 700,
      color: t.accentYellow,
      top: "50%", left: "50%",
      transform: "translate(-50%, -50%)",
      pointerEvents: "none",
    },
  };
}