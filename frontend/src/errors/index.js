// frontend/src/errors/index.js — the error hub. Which pattern to use:
//
//   What failed                                   Pattern                          Use
//   ─────────────────────────────────────────────────────────────────────────────────────────────
//   Data a card/page needs (useAsync error)       inline state + Retry             <ErrorState error onRetry={refetch}/>
//   Something the person just did (save/delete)   toast popup                      useToast().error(err, { title })
//   App-wide: offline / API unreachable           banner under the top bar         <ConnectionBanner/> (automatic)
//   A component throws while rendering            boundary around the area         <ErrorBoundary variant="section">
//   Session expired (401)                         modal (SessionExpiredModal)      automatic via apiClient
//   Form field input                              inline field message             stays in the form
//
// describeError(err) is the single place error wording lives; services throw ApiError.
export { default as ErrorState } from "./ErrorState";
export { default as ErrorBoundary } from "./ErrorBoundary";
export { default as ConnectionBanner } from "./ConnectionBanner";
export { ToastProvider, useToast } from "./ToastProvider";
export { describeError, ApiError } from "./errorCatalog";
export { reportError } from "./errorBus";
