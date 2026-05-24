/**
 * API base: use VITE_API_URL (e.g. http://127.0.0.1:8000) or the dev proxy prefix /api.
 */
export const API_BASE = import.meta.env.VITE_API_URL || '/api'

export function getToken() {
  return localStorage.getItem('access_token')
}

const USER_KEY = 'user_profile'

export function setToken(token) {
  localStorage.setItem('access_token', token)
}

export function clearToken() {
  localStorage.removeItem('access_token')
  localStorage.removeItem(USER_KEY)
}

export function getStoredUser() {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function setStoredUser(user) {
  if (user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  } else {
    localStorage.removeItem(USER_KEY)
  }
}

export async function fetchMe() {
  return api('/auth/me', { method: 'GET' })
}

function parseErrorDetail(detail) {
  if (!detail) return 'Request failed'
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (typeof d === 'object' && d.msg ? d.msg : String(d)))
      .join(', ')
  }
  return String(detail)
}

export async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  const token = getToken()
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  if (options.body && !(options.body instanceof FormData)) {
    if (!headers['Content-Type']) {
      headers['Content-Type'] = 'application/json'
    }
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })

  if (!res.ok) {
    let message = res.statusText
    try {
      const j = await res.json()
      message = parseErrorDetail(j.detail) || message
    } catch {
      /* ignore */
    }
    const err = new Error(message)
    err.status = res.status
    throw err
  }

  const ct = res.headers.get('content-type')
  if (ct && ct.includes('application/json')) {
    return res.json()
  }
  return res.text()
}

export async function loginRequest(email, password) {
  const body = new URLSearchParams()
  body.set('username', email)
  body.set('password', password)
  return api('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
}

export async function registerRequest(name, email, password) {
  return api('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ name, email, password }),
  })
}

export async function uploadResume(file) {
  const form = new FormData()
  form.append('file', file)
  return api('/resume/upload', {
    method: 'POST',
    body: form,
  })
}

export async function startInterview(role, numQuestions, options = {}) {
  const { company, interviewType } = options
  const body = {
    role,
    num_questions: numQuestions,
    ...(company != null && company !== '' ? { company } : {}),
    ...(interviewType != null && interviewType !== ''
      ? { interview_type: interviewType }
      : {}),
  }
  return api('/interview/start', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function submitAnswer(interviewId, questionId, answerText, speechMetrics = null) {
  return api('/interview/answer', {
    method: 'POST',
    body: JSON.stringify({
      interview_id: interviewId,
      question_id: questionId,
      answer_text: answerText,
      ...(speechMetrics ? { speech_metrics: speechMetrics } : {}),
    }),
  })
}

export async function analyzeInterview(interviewId) {
  return api(`/interview/${interviewId}/analyze`, { method: 'POST' })
}

export async function getProfile() {
  return api('/profile', { method: 'GET' })
}

export async function updateProfile(data) {
  return api('/profile', {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function changePassword(currentPassword, newPassword) {
  return api('/profile/change-password', {
    method: 'POST',
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  })
}

export async function getInterviewDetail(interviewId) {
  return api(`/interview/${interviewId}`, { method: 'GET' })
}

export async function deleteInterview(interviewId) {
  return api(`/interview/${interviewId}`, { method: 'DELETE' })
}

export async function nextQuestion(interviewId) {
  return api('/interview/next', {
    method: 'POST',
    body: JSON.stringify({ interview_id: interviewId }),
  })
}

export async function getInterviewHistory() {
  return api('/interview/history', { method: 'GET' })
}

export async function getInterviewDashboard() {
  return api('/interview/dashboard', { method: 'GET' })
}

/** Study Assistant (Groq + RAG) — matches backend /study/* routes */
export async function studyGetStatus() {
  return api('/study/status', { method: 'GET' })
}

export async function studyUploadPdf(file) {
  const form = new FormData()
  form.append('file', file)
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 5 * 60 * 1000)
  try {
    return await api('/study/upload-pdf', {
      method: 'POST',
      body: form,
      signal: controller.signal,
    })
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error('Upload timed out. Try a smaller PDF or wait for the server to finish loading models.')
    }
    throw err
  } finally {
    clearTimeout(timeoutId)
  }
}

export async function studyListPdfs() {
  return api('/study/uploaded-pdfs', { method: 'GET' })
}

export async function studyDeletePdf(pdfName) {
  return api(`/study/delete-pdf/${encodeURIComponent(pdfName)}`, { method: 'DELETE' })
}

async function studyApi(path, options = {}) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 3 * 60 * 1000)
  try {
    return await api(path, { ...options, signal: controller.signal })
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error(
        'Request timed out. The server may still be loading the embedding model — wait a minute and try again.',
      )
    }
    throw err
  } finally {
    clearTimeout(timeoutId)
  }
}

export async function studyAsk(question, pdfName = null) {
  return studyApi('/study/ask-question', {
    method: 'POST',
    body: JSON.stringify({
      question,
      ...(pdfName ? { pdf_name: pdfName } : {}),
    }),
  })
}

export async function studyChatHistory(limit = 50) {
  return api(`/study/chat-history?limit=${limit}`, { method: 'GET' })
}

export async function studyClearMemory() {
  return api('/study/clear-memory', { method: 'POST' })
}

function pdfGenerateBody({ pdfName = null, specification = null, extra = {} } = {}) {
  const spec = (specification || '').trim()
  return {
    ...(pdfName ? { pdf_name: pdfName } : {}),
    ...(spec ? { specification: spec } : {}),
    ...extra,
  }
}

export async function studyGenerateNotes({ pdfName = null, specification = null } = {}) {
  return studyApi('/study/generate-notes', {
    method: 'POST',
    body: JSON.stringify(pdfGenerateBody({ pdfName, specification })),
  })
}

export async function studyGenerateQuiz({
  pdfName = null,
  specification = null,
  numQuestions = 5,
} = {}) {
  return studyApi('/study/generate-quiz', {
    method: 'POST',
    body: JSON.stringify(
      pdfGenerateBody({ pdfName, specification, extra: { num_questions: numQuestions } }),
    ),
  })
}

export async function studyGenerateFlashcards({
  pdfName = null,
  specification = null,
  numCards = 5,
} = {}) {
  return studyApi('/study/generate-flashcards', {
    method: 'POST',
    body: JSON.stringify(
      pdfGenerateBody({ pdfName, specification, extra: { num_cards: numCards } }),
    ),
  })
}

export async function studyGenerateRoadmap(topic) {
  return studyApi('/study/generate-roadmap', {
    method: 'POST',
    body: JSON.stringify({ topic }),
  })
}

export async function studyCreatePlan(goal, currentLevel = 'Intermediate', weeks = 4) {
  return api('/study/study-plan', {
    method: 'POST',
    body: JSON.stringify({
      goal,
      current_level: currentLevel,
      weeks_available: weeks,
    }),
  })
}

export async function studyPlanHistory(planType = null, limit = 15) {
  const q = new URLSearchParams({ limit: String(limit) })
  if (planType) q.set('plan_type', planType)
  return api(`/study/plan-history?${q}`, { method: 'GET' })
}
