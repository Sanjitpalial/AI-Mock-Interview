import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { BarChart3, TrendingUp, Users, Target, Play, BookOpen, Trash2 } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'react-toastify'
import Layout from '../components/Layout'
import {
  getInterviewDashboard,
  getInterviewHistory,
  deleteInterview,
} from '../api/client'
import { useAuth } from '../context/AuthContext'
import { loadInterviewSession, clearInterviewSession } from '../utils/interviewSessionStorage'
import './Analytics.css'

const Analytics = () => {
  const navigate = useNavigate()
  const { isAuthenticated: authed, loading: authLoading } = useAuth()
  const [loading, setLoading] = useState(true)
  const [dashboard, setDashboard] = useState(null)
  const [history, setHistory] = useState([])

  const loadData = async () => {
    const [dash, hist] = await Promise.all([getInterviewDashboard(), getInterviewHistory()])
    setDashboard(dash)
    setHistory(Array.isArray(hist) ? hist : [])
  }

  useEffect(() => {
    if (authLoading) return
    if (!authed) {
      setLoading(false)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        await loadData()
      } catch (e) {
        if (!cancelled) toast.error(e.message || 'Could not load analytics')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [authed, authLoading])

  const handleDelete = async (interviewId, e) => {
    e.stopPropagation()
    if (!window.confirm('Delete this interview session permanently?')) return
    try {
      await deleteInterview(interviewId)
      const saved = loadInterviewSession()
      if (saved?.interviewId === interviewId) {
        clearInterviewSession()
      }
      setHistory((prev) => prev.filter((r) => r.interview_id !== interviewId))
      await loadData()
      toast.success('Interview deleted.')
    } catch (err) {
      toast.error(err.message || 'Could not delete interview')
    }
  }

  const total = dashboard?.total_interviews ?? 0
  const avgPct = Math.round((dashboard?.average_score ?? 0) * 100)

  const stats = [
    { label: 'Sessions (DB)', value: loading ? '…' : String(total), icon: BarChart3 },
    { label: 'Avg. overall score', value: loading ? '…' : `${avgPct}%`, icon: Target },
    { label: 'Focus areas', value: loading ? '…' : String(dashboard?.weak_topics?.length ?? 0), icon: TrendingUp },
    { label: 'Strength signals', value: loading ? '…' : String(dashboard?.strong_topics?.length ?? 0), icon: Users },
  ]

  return (
    <Layout>
      <main className="page-analytics container analytics-page__main">
        <motion.div className="analytics-page__header" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <span className="badge analytics-page__badge">Live data · PostgreSQL</span>
          <h1 className="analytics-page__title">Interview analytics</h1>
          <p className="analytics-page__desc">
            Aggregates from completed mock interviews (scores saved when you finish all questions).
          </p>
        </motion.div>

        {!authed && !authLoading && (
          <p className="analytics-page__desc" style={{ marginBottom: '1.5rem' }}>
            <Link to="/login">Sign in</Link> to see your dashboard and history.
          </p>
        )}

        <div className="grid grid--4 mb-section">
          {stats.map((s, i) => (
            <motion.div
              key={s.label}
              className="card"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.06 }}
            >
              <s.icon className="icon icon--md analytics-stat-card__icon" />
              <p className="stat-box__label">{s.label}</p>
              <p className="analytics-stat-card__value">{s.value}</p>
            </motion.div>
          ))}
        </div>

        {authed && dashboard && (
          <div className="grid grid--2 mb-section">
            <div className="card analytics-chart-placeholder">
              <h3 className="card__title">Areas to improve</h3>
              <ul style={{ margin: '0.75rem 0 0 1rem', padding: 0 }}>
                {(dashboard.weak_topics || []).map((t) => (
                  <li key={t}>{t}</li>
                ))}
              </ul>
            </div>
            <div className="card analytics-chart-placeholder">
              <h3 className="card__title">Strengths</h3>
              <ul style={{ margin: '0.75rem 0 0 1rem', padding: 0 }}>
                {(dashboard.strong_topics || []).map((t) => (
                  <li key={t}>{t}</li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {authed && history.length > 0 && (
          <div className="card mb-section">
            <h3 className="card__title">Recent interviews</h3>
            <div style={{ overflowX: 'auto' }}>
              <table className="analytics-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Role / context</th>
                    <th>Overall</th>
                    <th>Technical</th>
                    <th>When</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {history.map((row) => (
                    <tr
                      key={row.interview_id}
                      className="analytics-table__row"
                      onClick={() => navigate(`/history/${row.interview_id}`)}
                    >
                      <td>{row.interview_id}</td>
                      <td style={{ maxWidth: '280px' }}>{row.role}</td>
                      <td>
                        {row.total_score != null ? `${Math.round(row.total_score * 100)}%` : '—'}
                      </td>
                      <td>
                        {row.technical_score != null
                          ? `${Math.round(row.technical_score * 100)}%`
                          : '—'}
                      </td>
                      <td style={{ whiteSpace: 'nowrap' }}>{row.created_at?.slice(0, 10) || '—'}</td>
                      <td>
                        <button
                          type="button"
                          className="analytics-table__delete"
                          title="Delete session"
                          onClick={(e) => handleDelete(row.interview_id, e)}
                        >
                          <Trash2 className="icon icon--sm" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <div className="analytics-page__cta analytics-page__cta--row">
          <button
            type="button"
            className="btn btn--primary btn--lg"
            onClick={() => navigate('/interview')}
          >
            <Play className="icon" />
            Start mock interview
          </button>
          <button
            type="button"
            className="btn btn--secondary btn--lg"
            onClick={() => navigate('/', { state: { scrollTo: 'how-it-works' } })}
          >
            <BookOpen className="icon" />
            View how it works
          </button>
        </div>
      </main>
    </Layout>
  )
}

export default Analytics
