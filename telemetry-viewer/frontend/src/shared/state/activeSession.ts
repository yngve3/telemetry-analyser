const ACTIVE_SESSION_STORAGE_KEY = "telemetry-viewer-active-session-id";

export function readActiveSessionId(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem(ACTIVE_SESSION_STORAGE_KEY) ?? "";
}

export function writeActiveSessionId(sessionId: string): void {
  if (typeof window === "undefined") {
    return;
  }
  const trimmed = sessionId.trim();
  if (trimmed.length === 0) {
    window.localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY);
    return;
  }
  window.localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, trimmed);
}
