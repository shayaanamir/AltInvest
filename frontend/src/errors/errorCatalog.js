// frontend/src/errors/errorCatalog.js
// One place that turns any thrown value into something a person can read.
// Everything that shows an error (ErrorState, toasts, the boundary) goes through describeError().
import systemStates from "../content/systemStates.json";

export class ApiError extends Error {
  constructor(message, { status, kind, detail } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.kind = kind;
    this.detail = detail;
  }
}

// kind -> default copy. `useServerMessage` means a 4xx body's own message is specific
// enough to show ("Asset 'ZZZ' not found."); 5xx bodies can leak internals, so they never are.
const CATALOG = {
  network: {
    title: "Can't reach the server",
    message: "Check your connection, or the server may be down. Your data is safe.",
    retryable: true,
  },
  timeout: {
    title: "That took too long",
    message: "The server didn't answer in time. Try again.",
    retryable: true,
  },
  auth: {
    title: "You're signed out",
    message: "Your session has expired. Sign in again to continue.",
    retryable: false,
  },
  forbidden: {
    title: "Not allowed",
    message: "You don't have access to this.",
    retryable: false,
    useServerMessage: true,
  },
  notFound: {
    title: "Not found",
    message: "We couldn't find what you asked for.",
    retryable: false,
    useServerMessage: true,
  },
  validation: {
    title: "That didn't go through",
    message: "Some of the information wasn't accepted. Check it and try again.",
    retryable: false,
    useServerMessage: true,
  },
  rateLimit: {
    title: "Too many requests",
    message: "Slow down a moment and try again.",
    retryable: true,
    useServerMessage: true, // the server says how long to wait
  },
  server: {
    title: "Something went wrong on our side",
    message: "The server hit a problem. Try again in a moment.",
    retryable: true,
  },
  unavailable: {
    title: "Data is temporarily unavailable",
    message: "We couldn't reach the database right now. Try again shortly.",
    retryable: true,
  },
  partial: {
    title: "Only some of that worked",
    message: "Part of the request failed. Try again to finish it.",
    retryable: true,
    useServerMessage: true,
  },
  render: {
    title: systemStates.errorBoundary.title,
    message: "Part of this page failed to display.",
    retryable: true,
  },
  unknown: {
    title: "Something went wrong",
    message: systemStates.genericError.message,
    retryable: true,
  },
};

export function kindFromStatus(status) {
  if (status == null) return null;
  if (status === 401) return "auth";
  if (status === 403) return "forbidden";
  if (status === 404) return "notFound";
  if (status === 408) return "timeout";
  if (status === 429) return "rateLimit";
  if (status === 503) return "unavailable";
  if (status >= 500) return "server";
  if (status >= 400) return "validation";
  return null;
}

/**
 * @returns {{kind: string, title: string, message: string, retryable: boolean, status?: number, raw?: string}}
 *   `raw` is the technical text (for a "details" disclosure), never the headline.
 */
export function describeError(err, overrides = {}) {
  let kind = "unknown";
  if (err?.kind && CATALOG[err.kind]) kind = err.kind;
  else if (err?.name === "AbortError") kind = "timeout";
  else if (kindFromStatus(err?.status)) kind = kindFromStatus(err.status);
  else if (err instanceof TypeError && /fetch|network|load failed/i.test(err.message || "")) kind = "network";

  const entry = CATALOG[kind];
  const serverText = typeof err?.detail === "string" ? err.detail : null;
  const message = entry.useServerMessage && serverText ? serverText : entry.message;

  return {
    kind,
    title: entry.title,
    message,
    retryable: entry.retryable,
    status: err?.status,
    // Technical text for a "Details" disclosure. Never taken from an API response: 5xx bodies can
    // carry internals (hostnames, connection strings), so only client-side errors qualify.
    raw: !(err instanceof ApiError) && err?.message && err.message !== message ? err.message : undefined,
    ...overrides,
  };
}
