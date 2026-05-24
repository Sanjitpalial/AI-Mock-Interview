const STORAGE_KEY = 'careerai_active_interview'

export function saveInterviewSession(data) {
  try {
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ ...data, savedAt: Date.now() }),
    )
  } catch {
    /* quota / private mode */
  }
}

export function loadInterviewSession() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function clearInterviewSession() {
  try {
    sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    /* ignore */
  }
}
