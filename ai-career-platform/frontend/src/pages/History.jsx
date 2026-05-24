import { useEffect, useState, useCallback } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { toast } from 'react-toastify'
import { History as HistoryIcon, ChevronLeft, Mic, MessageSquare, Trash2 } from 'lucide-react'
import Layout from '../components/Layout'
import { useAuth } from '../context/AuthContext'
import { getInterviewHistory, getInterviewDetail, deleteInterview } from '../api/client'
import { loadInterviewSession, clearInterviewSession } from '../utils/interviewSessionStorage'
import './History.css'

function pct(v) {
  if (v == null || Number.isNaN(v)) return '—'
  return `${Math.round(Number(v) * 100)}%`
}

function InterviewList({ rows, onSelect, onDelete, deletingId }) {
  return (
    <div className="history-list">
      {rows.map((row) => (
        <div key={row.interview_id} className="history-card">
          <button
            type="button"
            className="history-card__main"
            onClick={() => onSelect(row.interview_id)}
          >
            <div className="history-card__top">
              <span className="history-card__id">Session #{row.interview_id}</span>
              <span className="history-card__score">
                {row.total_score != null ? pct(row.total_score) : 'In progress'}
              </span>
            </div>
            <p className="history-card__role">{row.role}</p>
            <p className="history-card__date">{row.created_at?.slice(0, 16).replace('T', ' ') || ''}</p>
          </button>
          <button
            type="button"
            className="history-card__delete"
            title="Delete session"
            disabled={deletingId === row.interview_id}
            onClick={() => onDelete(row.interview_id)}
          >
            <Trash2 className="icon icon--sm" />
          </button>
        </div>
      ))}
    </div>
  )
}

function InterviewDetailView({ detail, onDelete, deleting }) {
  return (
    <motion.div className="history-detail" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="history-detail__summary">
        <div className="history-detail__summary-head">
          <div>
            <h2>{detail.role}</h2>
            <div className="history-detail__scores">
              <span>Overall {pct(detail.total_score)}</span>
              <span>Technical {pct(detail.technical_score)}</span>
              <span>Communication {pct(detail.communication_score)}</span>
              <span>Confidence {pct(detail.confidence_score)}</span>
            </div>
            <p className="history-detail__date">
              {detail.created_at?.slice(0, 16).replace('T', ' ') || ''}
            </p>
          </div>
          <button
            type="button"
            className="history-detail__delete btn btn--danger"
            disabled={deleting}
            onClick={onDelete}
          >
            <Trash2 className="icon icon--sm" />
            {deleting ? 'Deleting…' : 'Delete session'}
          </button>
        </div>
      </div>

      {(detail.questions || []).map((q, idx) => (
        <article key={q.question_id} className="history-qa">
          <header className="history-qa__head">
            <span className="history-qa__num">Q{idx + 1}</span>
            {q.answer?.answer_mode === 'voice' && (
              <span className="history-qa__badge">
                <Mic className="icon icon--sm" /> Voice
              </span>
            )}
          </header>
          <p className="history-qa__question">{q.question_text}</p>
          {q.answer ? (
            <>
              <p className="history-qa__label">Your answer</p>
              <p className="history-qa__answer">{q.answer.answer_text}</p>
              <div className="history-qa__metrics">
                <span>
                  Overall{' '}
                  {pct(
                    (q.answer.technical_score +
                      q.answer.communication_score +
                      q.answer.confidence_score +
                      q.answer.grammar_score) /
                      4,
                  )}
                </span>
                <span>Tech {pct(q.answer.technical_score)}</span>
                <span>Comm {pct(q.answer.communication_score)}</span>
              </div>
              {q.answer.answer_mode === 'voice' && (
                <div className="history-qa__speech">
                  <strong>Speech analysis</strong>
                  <ul>
                    <li>Duration: {q.answer.speech_duration_sec ?? '—'}s</li>
                    <li>Pace: {q.answer.words_per_minute ?? '—'} WPM</li>
                    <li>Pauses: {q.answer.pause_count ?? 0}</li>
                    <li>Filler words: {q.answer.filler_count ?? 0}</li>
                    <li>
                      Vocabulary score:{' '}
                      {q.answer.vocabulary_score != null ? pct(q.answer.vocabulary_score) : '—'}
                    </li>
                    {q.answer.speech_metrics?.filler_words?.length > 0 && (
                      <li>Detected: {q.answer.speech_metrics.filler_words.join(', ')}</li>
                    )}
                  </ul>
                </div>
              )}
              {q.answer.ai_feedback && (
                <div className="history-qa__feedback">
                  <MessageSquare className="icon icon--sm" />
                  <span>{q.answer.ai_feedback}</span>
                </div>
              )}
            </>
          ) : (
            <p className="history-qa__muted">Not answered</p>
          )}
        </article>
      ))}
    </motion.div>
  )
}

export default function History() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { isAuthenticated, loading: authLoading } = useAuth()
  const [list, setList] = useState([])
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [deletingId, setDeletingId] = useState(null)

  const loadList = useCallback(async () => {
    const hist = await getInterviewHistory()
    setList(Array.isArray(hist) ? hist : [])
  }, [])

  const loadDetail = useCallback(async (interviewId) => {
    const d = await getInterviewDetail(interviewId)
    setDetail(d)
  }, [])

  useEffect(() => {
    if (authLoading) return
    if (!isAuthenticated) {
      setLoading(false)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        if (id) {
          await loadDetail(Number(id))
        } else {
          await loadList()
        }
      } catch (e) {
        if (!cancelled) toast.error(e.message || 'Could not load history')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [isAuthenticated, authLoading, id, loadList, loadDetail])

  const handleDelete = async (interviewId) => {
    if (!window.confirm('Delete this interview session permanently?')) return
    setDeletingId(interviewId)
    try {
      await deleteInterview(interviewId)
      const saved = loadInterviewSession()
      if (saved?.interviewId === interviewId) {
        clearInterviewSession()
      }
      toast.success('Interview deleted.')
      if (id && Number(id) === interviewId) {
        navigate('/history')
      } else {
        setList((prev) => prev.filter((r) => r.interview_id !== interviewId))
      }
    } catch (e) {
      toast.error(e.message || 'Could not delete interview')
    } finally {
      setDeletingId(null)
    }
  }

  if (!authLoading && !isAuthenticated) {
    return (
      <Layout>
        <main className="history-page">
          <div className="container">
            <p>
              <Link to="/login">Sign in</Link> to view your interview history.
            </p>
          </div>
        </main>
      </Layout>
    )
  }

  return (
    <Layout>
      <main className="history-page">
        <div className="container">
          <header className="history-page__header">
            <HistoryIcon className="icon icon--accent" />
            <h1>Interview history</h1>
            <p>Review every session — questions, answers, scores, and voice metrics.</p>
          </header>

          {id && (
            <button type="button" className="history-back btn btn--ghost" onClick={() => navigate('/history')}>
              <ChevronLeft className="icon" /> All sessions
            </button>
          )}

          {loading ? (
            <p className="history-page__loading">Loading…</p>
          ) : id ? (
            detail ? (
              <InterviewDetailView
                detail={detail}
                deleting={deletingId === detail.interview_id}
                onDelete={() => handleDelete(detail.interview_id)}
              />
            ) : (
              <p>Session not found.</p>
            )
          ) : list.length === 0 ? (
            <p className="history-empty">
              No interviews yet. <Link to="/interview">Start a mock interview</Link>.
            </p>
          ) : (
            <InterviewList
              rows={list}
              onSelect={(interviewId) => navigate(`/history/${interviewId}`)}
              onDelete={handleDelete}
              deletingId={deletingId}
            />
          )}
        </div>
      </main>
    </Layout>
  )
}
