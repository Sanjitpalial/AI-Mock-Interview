import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'react-toastify'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Mic,
  MicOff,
  ChevronRight,
  ArrowLeft,
  Brain,
  CheckCircle,
  RotateCcw,
  Play,
  Upload,
  FileText,
  Target,
  Star,
  Briefcase,
} from 'lucide-react'
import Layout from '../components/Layout'
import { uploadResume, startInterview, submitAnswer, analyzeInterview } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useSpeechRecognition } from '../hooks/useSpeechRecognition'
import {
  saveInterviewSession,
  loadInterviewSession,
  clearInterviewSession,
} from '../utils/interviewSessionStorage'
import './MockInterview.css'

const DEFAULT_NUM_QUESTIONS = 7

function overallPercent(scores) {
  if (!scores) return 0
  const t = scores.technical_accuracy ?? 0.5
  const c = scores.communication ?? 0.5
  const g = scores.grammar ?? 0.5
  const cf = scores.confidence ?? 0.5
  const s = scores.sentiment ?? 0.5
  return Math.round(((t + c + g + cf + s) / 5) * 100)
}

const roles = [
  'Software Engineer',
  'ML Engineer',
  'Data Scientist',
  'Product Manager',
  'Backend Engineer',
  'Full Stack Developer',
  'DevOps Engineer',
]
const interviewTypes = ['Technical', 'Behavioral', 'System Design', 'Mixed']

const MockInterview = () => {
  const navigate = useNavigate()
  const { isAuthenticated, loading: authLoading } = useAuth()
  const authed = isAuthenticated

  const [stage, setStage] = useState('setup')
  const [companyName, setCompanyName] = useState('')
  const [selectedRole, setSelectedRole] = useState('Software Engineer')
  const [selectedType, setSelectedType] = useState('Mixed')

  const [resumeFileName, setResumeFileName] = useState('')
  const [resumeReady, setResumeReady] = useState(false)
  const [uploadingResume, setUploadingResume] = useState(false)

  const [jdUploaded, setJdUploaded] = useState(false)
  const [jdFileName, setJdFileName] = useState('')

  const [interviewId, setInterviewId] = useState(null)
  const [questionId, setQuestionId] = useState(null)
  const [questionText, setQuestionText] = useState('')
  const [questionNumber, setQuestionNumber] = useState(1)
  const [totalQuestions, setTotalQuestions] = useState(DEFAULT_NUM_QUESTIONS)

  const [answer, setAnswer] = useState('')
  const [answerMode, setAnswerMode] = useState('text')
  const [sessionRows, setSessionRows] = useState([])
  const [interviewSummary, setInterviewSummary] = useState(null)
  const [loadingAction, setLoadingAction] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)

  const speech = useSpeechRecognition()
  const usedVoiceRef = useRef(false)
  const restoredRef = useRef(false)
  const sessionSnapshotRef = useRef(null)

  const inFocusMode = stage === 'interview'
  const hasPausedInterview = Boolean(interviewId) && stage === 'setup'

  const persistSession = (overrides = {}) => {
    if (!interviewId && stage === 'setup' && !overrides.interviewId) return
    saveInterviewSession({
      stage,
      companyName,
      selectedRole,
      selectedType,
      resumeFileName,
      resumeReady,
      jdUploaded,
      jdFileName,
      interviewId,
      questionId,
      questionText,
      questionNumber,
      totalQuestions,
      answer,
      sessionRows,
      ...overrides,
    })
  }

  useEffect(() => {
    if (restoredRef.current) return
    restoredRef.current = true
    const saved = loadInterviewSession()
    if (!saved?.interviewId) return

    setStage(saved.stage === 'results' ? 'results' : saved.stage === 'interview' ? 'interview' : 'setup')
    setCompanyName(saved.companyName || '')
    setSelectedRole(saved.selectedRole || 'Software Engineer')
    setSelectedType(saved.selectedType || 'Mixed')
    setResumeFileName(saved.resumeFileName || '')
    setResumeReady(Boolean(saved.resumeReady))
    setJdUploaded(Boolean(saved.jdUploaded))
    setJdFileName(saved.jdFileName || '')
    setInterviewId(saved.interviewId)
    setQuestionId(saved.questionId)
    setQuestionText(saved.questionText || '')
    setQuestionNumber(saved.questionNumber || 1)
    setTotalQuestions(saved.totalQuestions || DEFAULT_NUM_QUESTIONS)
    setAnswer(saved.answer || '')
    setSessionRows(Array.isArray(saved.sessionRows) ? saved.sessionRows : [])
    setInterviewSummary(saved.interviewSummary || null)

    if (saved.stage === 'interview') {
      toast.info('Interview restored — pick up where you left off.')
    } else if (saved.stage === 'setup' && saved.interviewId) {
      toast.info('Paused interview found — tap Resume to continue.')
    }
  }, [])

  sessionSnapshotRef.current = {
    stage,
    companyName,
    selectedRole,
    selectedType,
    resumeFileName,
    resumeReady,
    jdUploaded,
    jdFileName,
    interviewId,
    questionId,
    questionText,
    questionNumber,
    totalQuestions,
    answer,
    sessionRows,
    interviewSummary,
  }

  useEffect(() => {
    if (!interviewId) return
    persistSession()
  }, [
    stage,
    interviewId,
    questionId,
    questionText,
    questionNumber,
    totalQuestions,
    answer,
    sessionRows,
    interviewSummary,
    companyName,
    selectedRole,
    selectedType,
    resumeReady,
  ])

  useEffect(() => {
    return () => {
      if (sessionSnapshotRef.current?.interviewId) {
        saveInterviewSession(sessionSnapshotRef.current)
      }
    }
  }, [])

  useEffect(() => {
    if (inFocusMode) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [inFocusMode])

  useEffect(() => {
    if (speech.listening) {
      setAnswer(speech.transcript)
    }
  }, [speech.listening, speech.transcript])

  const toggleVoice = () => {
    if (!speech.supported) {
      toast.error('Voice input needs Chrome or Edge with microphone access.')
      return
    }
    if (speech.listening) {
      speech.stop()
      setAnswer(speech.transcript || answer)
      setAnswerMode('voice')
      usedVoiceRef.current = true
      return
    }
    try {
      usedVoiceRef.current = true
      setAnswerMode('voice')
      speech.start()
      toast.info('Listening… speak your answer, then click Stop Recording.')
    } catch (err) {
      toast.error(err.message || 'Could not start microphone')
    }
  }

  const handleResumeFile = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      toast.error('Please upload a PDF resume.')
      return
    }
    setUploadingResume(true)
    try {
      await uploadResume(file)
      setResumeReady(true)
      setResumeFileName(file.name)
      toast.success('Resume saved — ready for interview.')
    } catch (err) {
      toast.error(err.message || 'Resume upload failed')
    } finally {
      setUploadingResume(false)
    }
  }

  const handleJdUpload = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      setJdUploaded(true)
      setJdFileName(file.name)
    }
  }

  const handleStartInterview = async () => {
    if (!authed) {
      toast.info('Please sign in first.')
      navigate('/login')
      return
    }
    if (!resumeReady) {
      toast.error('Upload your resume (PDF) first.')
      return
    }
    const company = companyName.trim()
    if (!company) {
      toast.error('Enter the company name you are interviewing for.')
      return
    }
    setLoadingAction(true)
    try {
      const data = await startInterview(selectedRole, DEFAULT_NUM_QUESTIONS, {
        company,
        interviewType: selectedType,
      })
      setInterviewId(data.interview_id)
      setQuestionId(data.question_id)
      setQuestionText(data.question || '')
      setQuestionNumber(data.question_number || 1)
      setTotalQuestions(data.total_questions || DEFAULT_NUM_QUESTIONS)
      setSessionRows([])
      setAnswer('')
      speech.reset()
      usedVoiceRef.current = false
      setAnswerMode('text')
      setStage('interview')
      persistSession({
        stage: 'interview',
        interviewId: data.interview_id,
        questionId: data.question_id,
        questionText: data.question || '',
        questionNumber: data.question_number || 1,
        totalQuestions: data.total_questions || DEFAULT_NUM_QUESTIONS,
        sessionRows: [],
      })
    } catch (err) {
      toast.error(err.message || 'Could not start interview')
    } finally {
      setLoadingAction(false)
    }
  }

  const runBatchAnalysis = async () => {
    if (!interviewId) return
    setStage('analyzing')
    setAnalyzing(true)
    persistSession({ stage: 'analyzing' })
    try {
      const data = await analyzeInterview(interviewId)
      const rows = (data.questions || []).map((q) => ({
        question: q.question,
        answer: q.answer,
        scores: q.scores,
        speech: q.speech_analysis,
        overall: q.overall_percent ?? overallPercent(q.scores),
      }))
      setSessionRows(rows)
      setInterviewSummary(data.summary || null)
      setStage('results')
      persistSession({
        stage: 'results',
        sessionRows: rows,
        interviewSummary: data.summary,
      })
    } catch (err) {
      toast.error(err.message || 'Analysis failed. Try again from History.')
      setStage('interview')
      persistSession({ stage: 'interview' })
    } finally {
      setAnalyzing(false)
    }
  }

  const handleSubmitAnswer = async () => {
    if (!answer.trim() || !interviewId || !questionId) return
    if (speech.listening) {
      speech.stop()
    }

    setLoadingAction(true)
    try {
      const speechMetrics =
        usedVoiceRef.current || answerMode === 'voice'
          ? {
              answer_mode: 'voice',
              duration_sec: speech.durationSec || speech.getMetrics('voice').duration_sec,
              pause_count: speech.pauseCount,
            }
          : null

      const res = await submitAnswer(interviewId, questionId, answer.trim(), speechMetrics)
      setSessionRows((prev) => [
        ...prev,
        {
          question: questionText,
          answer: answer.trim(),
          speech: res.speech_analysis,
          pending: true,
        },
      ])
      setAnswer('')
      speech.reset()
      usedVoiceRef.current = false
      setAnswerMode('text')

      if (res.next_question_error) {
        toast.warning(res.next_question_error)
      }

      const finished = res.interview_complete || !res.next_question
      if (finished) {
        await runBatchAnalysis()
        return
      }

      const n = res.next_question
      setQuestionId(n.question_id)
      setQuestionText(n.question || '')
      setQuestionNumber(n.question_number)
      setTotalQuestions((t) => n.total_questions ?? t)
    } catch (err) {
      toast.error(err.message || 'Failed to submit answer')
    } finally {
      setLoadingAction(false)
    }
  }

  const handlePauseInterview = () => {
    if (speech.listening) speech.stop()
    setStage('setup')
    persistSession({ stage: 'setup' })
    toast.info('Interview paused. Your progress is saved — resume anytime from this page.')
  }

  const handleResumeInterview = () => {
    if (!interviewId || !questionId) {
      toast.error('No saved interview to resume.')
      return
    }
    setStage('interview')
    persistSession({ stage: 'interview' })
  }

  const handleReset = () => {
    clearInterviewSession()
    setStage('setup')
    setAnswer('')
    setSessionRows([])
    setInterviewSummary(null)
    setInterviewId(null)
    setQuestionId(null)
    setQuestionText('')
    setQuestionNumber(1)
    setResumeReady(false)
    setResumeFileName('')
    setJdUploaded(false)
    setJdFileName('')
    speech.reset()
    usedVoiceRef.current = false
    setAnswerMode('text')
  }

  const avgScore =
    sessionRows.length === 0
      ? 0
      : Math.round(
          sessionRows.reduce((a, r) => a + r.overall, 0) / sessionRows.length,
        )

  const getScoreClass = (score) => {
    if (score >= 85) return 'interview-analysis-item__score--high'
    if (score >= 70) return 'interview-analysis-item__score--mid'
    return 'interview-analysis-item__score--low'
  }

  const summaryFeedback = interviewSummary?.overall_feedback || []
  const summaryStrengths = interviewSummary?.strengths || []
  const summaryImprovements = interviewSummary?.improvements || []
  const summarySentiment = interviewSummary?.sentiment_summary || ''
  const speechTips = interviewSummary?.speech_tips || []

  const interviewStageUI = (
    <motion.div
      key="interview"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
    >
      <div className="interview-panel interview-progress">
        <div className="interview-progress__meta">
          <span>
            Question {questionNumber} of {totalQuestions}
          </span>
          <span>
            {companyName.trim() || 'Your company'} · {selectedRole}
          </span>
        </div>
        <div className="interview-progress__bar">
          <motion.div
            className="interview-progress__fill"
            initial={false}
            animate={{
              width: `${(questionNumber / totalQuestions) * 100}%`,
            }}
            transition={{ duration: 0.3 }}
          />
        </div>
      </div>

      <div className="interview-panel interview-question">
        <div className="interview-question__agent">
          <div className="interview-question__avatar">
            <Brain className="icon" />
          </div>
          <div>
            <div className="interview-question__agent-name">Interview Agent</div>
            <div className="interview-question__tags">
              <span className="interview-tag interview-tag--type">{selectedType}</span>
              <span className="interview-tag">Live</span>
            </div>
          </div>
        </div>
        <p className="interview-question__text">{questionText}</p>
      </div>

      <div className="interview-panel">
        <div className="interview-answer__header">
          <h3>Your Answer</h3>
          <button
            type="button"
            onClick={toggleVoice}
            disabled={!speech.supported}
            className={`interview-voice-btn ${speech.listening ? 'interview-voice-btn--active' : ''}`}
            title={speech.supported ? 'Use microphone' : 'Use Chrome or Edge for voice'}
          >
            {speech.listening ? <MicOff className="icon icon--sm" /> : <Mic className="icon icon--sm" />}
            {speech.listening ? 'Stop Recording' : 'Voice Answer'}
          </button>
        </div>
        {speech.listening && (
          <div className="interview-recording-banner">
            <span className="interview-recording-dot" />
            Listening… pauses and fillers are tracked for evaluation.
          </div>
        )}
        {!speech.supported && (
          <p className="interview-upload__hint" style={{ marginTop: '0.5rem' }}>
            Voice input works best in Chrome or Edge with microphone permission enabled.
          </p>
        )}
        <textarea
          className="interview-textarea"
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="Type your answer here…"
          rows={8}
        />
        <div className="interview-answer__footer">
          <span className="interview-char-count">{answer.length} characters</span>
          <button
            type="button"
            onClick={handleSubmitAnswer}
            disabled={!answer.trim() || loadingAction}
            className="btn btn--primary"
            style={{ opacity: answer.trim() && !loadingAction ? 1 : 0.45 }}
          >
            {loadingAction
              ? 'Saving answer…'
              : questionNumber >= totalQuestions
                ? 'Finish Interview'
                : 'Next Question'}
            <ChevronRight className="icon" />
          </button>
        </div>
      </div>
    </motion.div>
  )

  if (inFocusMode) {
    return (
      <div className="interview-focus-shell">
        <div className="interview-page-v2 interview-page-v2--focus">
          <header className="interview-focus-bar">
            <button type="button" className="interview-focus-bar__back" onClick={handlePauseInterview}>
              <ArrowLeft className="icon icon--sm" />
              Back
            </button>
            <span className="interview-focus-bar__meta">
              Question {questionNumber} / {totalQuestions} · progress saved automatically
            </span>
          </header>
          <div className="container container--focus">
            <AnimatePresence mode="wait">{interviewStageUI}</AnimatePresence>
          </div>
        </div>
      </div>
    )
  }

  return (
    <Layout>
      <div className="interview-page-v2">
        <div className="container container--mid">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="interview-page-v2__header"
          >
            <h1 className="interview-page-v2__title">AI Mock Interview</h1>
            <p className="interview-page-v2__subtitle">
              {DEFAULT_NUM_QUESTIONS} AI-powered questions tailored to your role and company
            </p>
            {!authed && (
              <p style={{ marginTop: '0.75rem', color: 'var(--muted)' }}>
                <Link to="/login">Sign in</Link> to upload your resume and run a live interview.
              </p>
            )}
          </motion.div>

          <AnimatePresence mode="wait">
            {stage === 'setup' && (
              <motion.div
                key="setup"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -12 }}
              >
                {hasPausedInterview && (
                  <div className="interview-resume-banner">
                    <p>
                      You have a paused interview — <strong>Question {questionNumber}</strong> of{' '}
                      {totalQuestions} ({companyName.trim() || 'your company'} · {selectedRole}). Progress
                      is saved if you leave this page.
                    </p>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <button type="button" className="btn btn--primary" onClick={handleResumeInterview}>
                        <Play className="icon" />
                        Resume interview
                      </button>
                      <button
                        type="button"
                        className="btn btn--secondary"
                        onClick={() => {
                          if (window.confirm('Discard this interview and start fresh?')) handleReset()
                        }}
                      >
                        Discard
                      </button>
                    </div>
                  </div>
                )}
                <div className="interview-panel">
                  <h2 className="interview-panel__title">
                    <FileText className="icon" />
                    Resume Upload
                  </h2>
                  <label
                    className={`interview-upload ${resumeReady ? 'interview-upload--done' : ''}`}
                    style={{ cursor: authed ? 'pointer' : 'not-allowed', opacity: authed ? 1 : 0.6 }}
                  >
                    <input
                      type="file"
                      accept=".pdf,application/pdf"
                      disabled={!authed || uploadingResume}
                      onChange={handleResumeFile}
                    />
                    {resumeReady ? (
                      <>
                        <CheckCircle
                          className="icon icon--lg"
                          style={{ margin: '0 auto', color: 'var(--success)' }}
                        />
                        <p className="interview-upload__text">{resumeFileName || 'resume.pdf'}</p>
                        <p className="interview-upload__hint">Resume stored — you can start the interview</p>
                      </>
                    ) : (
                      <>
                        <Upload className="icon icon--lg icon--muted" style={{ margin: '0 auto' }} />
                        <p className="interview-upload__text">
                          {uploadingResume ? 'Uploading…' : 'Drop your resume here or click (PDF only)'}
                        </p>
                        <p className="interview-upload__hint">PDF up to 10MB</p>
                      </>
                    )}
                  </label>
                </div>

                <div className="interview-panel">
                  <h2 className="interview-panel__title">
                    <Briefcase className="icon" />
                    Job Description (optional)
                  </h2>
                  <label className={`interview-upload ${jdUploaded ? 'interview-upload--done' : ''}`}>
                    <input type="file" accept=".pdf,.doc,.docx,.txt" onChange={handleJdUpload} />
                    {jdUploaded ? (
                      <>
                        <CheckCircle
                          className="icon icon--lg"
                          style={{ margin: '0 auto', color: 'var(--success)' }}
                        />
                        <p className="interview-upload__text">{jdFileName}</p>
                        <p className="interview-upload__hint">For your prep notes (optional; interview uses resume + role settings)</p>
                      </>
                    ) : (
                      <>
                        <Upload className="icon icon--lg icon--muted" style={{ margin: '0 auto' }} />
                        <p className="interview-upload__text">Upload job description (optional)</p>
                        <p className="interview-upload__hint">Helps you align answers with the role</p>
                      </>
                    )}
                  </label>
                </div>

                <div className="interview-panel">
                  <h2 className="interview-panel__title">
                    <Target className="icon" />
                    Interview Configuration
                  </h2>
                  <div className="interview-config">
                    <div className="interview-field">
                      <label className="interview-field__label" htmlFor="company">
                        Target Company
                      </label>
                      <input
                        id="company"
                        type="text"
                        className="interview-field__input"
                        placeholder="e.g. Acme Corp, Stripe, your startup name…"
                        value={companyName}
                        onChange={(e) => setCompanyName(e.target.value)}
                        autoComplete="organization"
                      />
                      <p className="interview-field__hint">
                        Questions are tailored to this company and your role.
                      </p>
                    </div>
                    <div className="interview-config__row">
                      <div className="interview-field">
                        <label className="interview-field__label" htmlFor="role">
                          Target Role
                        </label>
                        <select
                          id="role"
                          className="interview-field__select"
                          value={selectedRole}
                          onChange={(e) => setSelectedRole(e.target.value)}
                        >
                          {roles.map((r) => (
                            <option key={r} value={r}>
                              {r}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="interview-field">
                        <label className="interview-field__label" htmlFor="type">
                          Interview Type
                        </label>
                        <select
                          id="type"
                          className="interview-field__select"
                          value={selectedType}
                          onChange={(e) => setSelectedType(e.target.value)}
                        >
                          {interviewTypes.map((t) => (
                            <option key={t} value={t}>
                              {t}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleStartInterview}
                  disabled={loadingAction || !authed || hasPausedInterview}
                  className="interview-start-btn"
                >
                  <Play className="icon" />
                  {loadingAction
                    ? 'Starting…'
                    : `Start ${selectedType} Interview${companyName.trim() ? ` at ${companyName.trim()}` : ''}`}
                </button>
              </motion.div>
            )}

            {stage === 'analyzing' && (
              <motion.div
                key="analyzing"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -12 }}
                className="interview-panel interview-analyzing"
              >
                <div className="interview-analyzing__spinner" aria-hidden />
                <h2 className="interview-panel__title">Analyzing your interview</h2>
                <p className="interview-analyzing__sub">
                  Running AI evaluation, speech metrics, and sentiment analysis on all {sessionRows.length}{' '}
                  answers…
                </p>
              </motion.div>
            )}

            {stage === 'results' && (
              <motion.div
                key="results"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -12 }}
              >
                <div className="interview-panel interview-results-score">
                  <div className="interview-results-score__circle">{avgScore}%</div>
                  <h2 className="interview-results-score__title">Interview Complete</h2>
                  <p className="interview-results-score__sub">
                    Full analysis: technical, communication, speech, and sentiment
                  </p>
                  <div className="interview-stars">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <Star
                        key={star}
                        className={`icon ${star <= Math.round(avgScore / 20) ? 'icon--filled' : 'icon--empty'}`}
                      />
                    ))}
                  </div>
                </div>

                {(summaryStrengths.length > 0 || summaryImprovements.length > 0) && (
                  <div className="interview-panel interview-summary-grid">
                    {summaryStrengths.length > 0 && (
                      <div className="interview-summary-block">
                        <h4 className="interview-summary-block__title">Strengths</h4>
                        <ul>
                          {summaryStrengths.map((s, i) => (
                            <li key={i}>{s}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {summaryImprovements.length > 0 && (
                      <div className="interview-summary-block">
                        <h4 className="interview-summary-block__title">Areas to improve</h4>
                        <ul>
                          {summaryImprovements.map((s, i) => (
                            <li key={i}>{s}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                <div className="interview-panel">
                  <h3 className="interview-panel__title">Per-question breakdown</h3>
                  {sessionRows.map((row, i) => (
                    <div key={i} className="interview-analysis-item">
                      <div className="interview-analysis-item__head">
                        <p className="interview-analysis-item__q">{row.question}</p>
                        <span className={`interview-analysis-item__score ${getScoreClass(row.overall)}`}>
                          {row.overall}%
                        </span>
                      </div>
                      <p className="interview-analysis-item__answer">{row.answer}</p>
                      <div className="interview-metrics">
                        <div className="interview-metric">
                          <div className="interview-metric__label">Technical</div>
                          <div className="interview-metric__value">
                            {Math.round((row.scores?.technical_accuracy ?? 0) * 100)}%
                          </div>
                        </div>
                        <div className="interview-metric">
                          <div className="interview-metric__label">Communication</div>
                          <div className="interview-metric__value">
                            {Math.round((row.scores?.communication ?? 0) * 100)}%
                          </div>
                        </div>
                        <div className="interview-metric">
                          <div className="interview-metric__label">Confidence</div>
                          <div className="interview-metric__value">
                            {Math.round((row.scores?.confidence ?? 0) * 100)}%
                          </div>
                        </div>
                        <div className="interview-metric">
                          <div className="interview-metric__label">Sentiment</div>
                          <div className="interview-metric__value">
                            {Math.round((row.scores?.sentiment ?? 0) * 100)}%
                          </div>
                        </div>
                      </div>
                      {row.speech && (
                        <div className="interview-speech-block">
                          <h4 className="interview-speech-block__title">Speech analysis</h4>
                          <div className="interview-metrics">
                            <div className="interview-metric">
                              <div className="interview-metric__label">Mode</div>
                              <div className="interview-metric__value">{row.speech.answer_mode || 'text'}</div>
                            </div>
                            <div className="interview-metric">
                              <div className="interview-metric__label">Words</div>
                              <div className="interview-metric__value">{row.speech.word_count ?? '—'}</div>
                            </div>
                            <div className="interview-metric">
                              <div className="interview-metric__label">Fillers</div>
                              <div className="interview-metric__value">{row.speech.filler_count ?? 0}</div>
                            </div>
                            <div className="interview-metric">
                              <div className="interview-metric__label">Fluency</div>
                              <div className="interview-metric__value">
                                {Math.round((row.speech.fluency_score ?? 0) * 100)}%
                              </div>
                            </div>
                            {row.speech.words_per_minute != null && (
                              <div className="interview-metric">
                                <div className="interview-metric__label">Pace (WPM)</div>
                                <div className="interview-metric__value">{row.speech.words_per_minute}</div>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                      {Array.isArray(row.scores?.feedback) && row.scores.feedback.length > 0 && (
                        <ul className="interview-q-feedback">
                          {row.scores.feedback.map((line, j) => (
                            <li key={j}>{line}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))}
                </div>

                <div className="interview-panel interview-feedback">
                  <div className="interview-feedback__head">
                    <Brain className="icon icon--accent" />
                    <h3 className="interview-panel__title" style={{ marginBottom: 0 }}>
                      Coach feedback
                    </h3>
                  </div>
                  <div className="interview-feedback__body">
                    {summaryFeedback.length > 0 ? (
                      summaryFeedback.map((line, idx) => <p key={idx}>{line}</p>)
                    ) : (
                      <p>Review the per-question breakdown above.</p>
                    )}
                    {summarySentiment && (
                      <p className="interview-feedback__highlight">
                        <strong>Sentiment:</strong> {summarySentiment}
                      </p>
                    )}
                    {speechTips.length > 0 && (
                      <div className="interview-feedback__speech-tips">
                        <strong>Speech tips:</strong>
                        <ul>
                          {speechTips.map((t, i) => (
                            <li key={i}>{t}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>

                <div className="interview-start-btn" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  <button
                    type="button"
                    onClick={() => navigate('/history')}
                    className="btn btn--primary btn--full"
                  >
                    View full history & speech analysis
                  </button>
                  <button type="button" onClick={handleReset} className="btn btn--secondary btn--full">
                    <RotateCcw className="icon" />
                    Start New Interview
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </Layout>
  )
}

export default MockInterview
