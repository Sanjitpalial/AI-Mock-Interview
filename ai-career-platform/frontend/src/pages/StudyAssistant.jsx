import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'react-toastify'
import {
  BookOpen,
  FileText,
  HelpCircle,
  Layers,
  Loader2,
  Map,
  MessageSquarePlus,
  NotebookPen,
  Send,
  Sparkles,
  Trash2,
  Upload,
} from 'lucide-react'
import Layout from '../components/Layout'
import { useAuth } from '../context/AuthContext'
import {
  studyAsk,
  studyChatHistory,
  studyClearMemory,
  studyCreatePlan,
  studyDeletePdf,
  studyGenerateFlashcards,
  studyGenerateNotes,
  studyGenerateQuiz,
  studyGenerateRoadmap,
  studyListPdfs,
  studyPlanHistory,
  studyUploadPdf,
} from '../api/client'
import './StudyAssistant.css'

const FEATURES = [
  { id: 'chat', label: 'Chat', icon: HelpCircle },
  { id: 'notes', label: 'Notes', icon: NotebookPen },
  { id: 'quiz', label: 'Quiz', icon: Sparkles },
  { id: 'cards', label: 'Flashcards', icon: Layers },
  { id: 'roadmap', label: 'Roadmap', icon: Map },
  { id: 'plan', label: 'Study plan', icon: BookOpen },
]

function truncate(str, max = 42) {
  if (!str) return 'Untitled'
  const s = String(str).trim()
  return s.length > max ? `${s.slice(0, max)}…` : s
}

function formatWhen(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

const StudyAssistant = () => {
  const navigate = useNavigate()
  const { isAuthenticated, loading: authLoading } = useAuth()
  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)

  const [pdfs, setPdfs] = useState([])
  const [chats, setChats] = useState([])
  const [selectedPdf, setSelectedPdf] = useState(null)
  const [activeChatId, setActiveChatId] = useState(null)

  const [feature, setFeature] = useState('chat')
  const [messages, setMessages] = useState([])
  const [question, setQuestion] = useState('')
  const [uploading, setUploading] = useState(false)
  const [busy, setBusy] = useState(false)

  const [specification, setSpecification] = useState('')
  const [toolPdf, setToolPdf] = useState(null)
  const [numItems, setNumItems] = useState(5)
  const [planGoal, setPlanGoal] = useState('')
  const [planWeeks, setPlanWeeks] = useState(4)
  const [output, setOutput] = useState('')
  const [savedPlans, setSavedPlans] = useState([])

  const refreshSidebar = useCallback(async () => {
    if (!isAuthenticated) return
    try {
      const [pdfRes, chatRes] = await Promise.all([
        studyListPdfs(),
        studyChatHistory(80),
      ])
      setPdfs(pdfRes.uploaded_pdfs || [])
      setChats(Array.isArray(chatRes) ? chatRes : [])
    } catch (err) {
      toast.error(err.message || 'Could not load study data')
    }
  }, [isAuthenticated])

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      refreshSidebar()
      studyPlanHistory(null, 12).then(setSavedPlans).catch(() => {})
      import('../api/client').then(({ studyGetStatus }) =>
        studyGetStatus().then((s) => {
          if (!s.groq_configured) {
            toast.warning(
              s.detail ||
                'GROQ_API_KEY is missing on the server — chat and generation will not work.',
              { autoClose: 10000 },
            )
          } else if (s.groq_working === false) {
            toast.error(
              s.detail ||
                'Groq API key is invalid. Update GROQ_API_KEY in backend/.env and restart the backend.',
              { autoClose: 12000 },
            )
          }
        }),
      )
    }
  }, [authLoading, isAuthenticated, refreshSidebar])

  useEffect(() => {
    if (selectedPdf && !toolPdf) setToolPdf(selectedPdf)
  }, [selectedPdf, toolPdf])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, output, busy])

  const handleNewChat = async () => {
    setActiveChatId(null)
    setMessages([])
    setOutput('')
    try {
      if (isAuthenticated) await studyClearMemory()
    } catch {
      /* optional */
    }
  }

  const handleSelectChat = (chat) => {
    setActiveChatId(chat.id)
    setFeature('chat')
    setMessages([
      { role: 'user', text: chat.question },
      {
        role: 'assistant',
        text: chat.answer,
        sources: chat.sources || [],
      },
    ])
    if (chat.sources?.[0]) setSelectedPdf(chat.sources[0])
  }

  const processPdfUpload = async (file) => {
    if (!file) return
    if (!isAuthenticated) {
      toast.info('Please sign in to upload PDFs')
      navigate('/login')
      return
    }
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      toast.error('Only PDF files are supported')
      return
    }

    setUploading(true)
    toast.info('Uploading and indexing PDF… first upload may take up to a minute.')
    try {
      const res = await studyUploadPdf(file)
      const chunks = res.total_chunks ?? 0
      if (chunks > 0) {
        toast.success(`Indexed ${chunks} chunks from ${res.file_name || file.name}`)
        setSelectedPdf(res.file_name || res.filename || file.name)
        setFeature('chat')
      } else {
        toast.warning(res.message || 'PDF saved but no chunks indexed')
      }
      await refreshSidebar()
    } catch (err) {
      const msg = err.message || 'Upload failed'
      if (err.status === 401) {
        toast.error('Session expired — please sign in again')
        navigate('/login')
      } else if (err.status === 503 && msg.includes('GROQ')) {
        toast.error('Server config issue — PDF indexing should still work; check backend logs.')
      } else {
        toast.error(msg)
      }
    } finally {
      setUploading(false)
    }
  }

  const handleUpload = async (e) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    await processPdfUpload(file)
  }

  const openFilePicker = () => {
    if (!isAuthenticated) {
      toast.info('Please sign in first')
      navigate('/login')
      return
    }
    fileInputRef.current?.click()
  }

  const handleDeletePdf = async (fileName, e) => {
    e?.stopPropagation()
    try {
      await studyDeletePdf(fileName)
      if (selectedPdf === fileName) setSelectedPdf(null)
      toast.success('PDF removed')
      await refreshSidebar()
    } catch (err) {
      toast.error(err.message || 'Delete failed')
    }
  }

  const handleAsk = async (ev) => {
    ev.preventDefault()
    const q = question.trim()
    if (!q) return
    if (!pdfs.length) {
      toast.info('Upload a PDF in the sidebar first')
      return
    }
    setBusy(true)
    setMessages((prev) => [...prev, { role: 'user', text: q }])
    setQuestion('')
    try {
      const res = await studyAsk(q, selectedPdf)
      const answer = res.answer ?? res.message ?? 'No answer returned'
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: answer, sources: res.sources || [] },
      ])
      await refreshSidebar()
      setActiveChatId(null)
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: err.message || 'Request failed', error: true },
      ])
    } finally {
      setBusy(false)
    }
  }

  const runGenerator = async () => {
    const isPdfFeature = ['notes', 'quiz', 'cards'].includes(feature)

    if (isPdfFeature && !pdfs.length) {
      toast.info('Upload a PDF first')
      return
    }
    if (feature === 'plan' && !planGoal.trim()) {
      toast.info('Enter a learning goal')
      return
    }
    if (feature === 'roadmap' && !specification.trim()) {
      toast.info('Enter a topic for the roadmap')
      return
    }

    const pdfName = toolPdf || selectedPdf || null
    const spec = specification.trim() || null
    const scopeHint = spec
      ? `(${spec})`
      : pdfName
        ? `(full PDF: ${truncate(pdfName, 24)})`
        : '(all your PDFs)'

    setBusy(true)
    setOutput('')
    try {
      let res
      switch (feature) {
        case 'notes':
          toast.info(`Generating notes from your PDF ${scopeHint}…`)
          res = await studyGenerateNotes({ pdfName, specification: spec })
          setOutput(res.generated_notes || res.message || '')
          break
        case 'quiz':
          toast.info(`Generating quiz from your PDF ${scopeHint}…`)
          res = await studyGenerateQuiz({
            pdfName,
            specification: spec,
            numQuestions: numItems,
          })
          setOutput(res.quiz || res.message || '')
          break
        case 'cards':
          toast.info(`Generating flashcards from your PDF ${scopeHint}…`)
          res = await studyGenerateFlashcards({
            pdfName,
            specification: spec,
            numCards: numItems,
          })
          setOutput(res.flashcards || res.message || '')
          break
        case 'roadmap':
          res = await studyGenerateRoadmap(specification.trim())
          setOutput(res.roadmap || res.message || '')
          break
        case 'plan':
          res = await studyCreatePlan(planGoal.trim(), 'Intermediate', planWeeks)
          setOutput(res.study_plan || res.message || '')
          break
        default:
          break
      }
      if (['roadmap', 'plan'].includes(feature)) {
        const plans = await studyPlanHistory(null, 12)
        setSavedPlans(plans)
      }
      toast.success('Done')
    } catch (err) {
      toast.error(err.message || 'Generation failed')
    } finally {
      setBusy(false)
    }
  }

  const renderMain = () => {
    if (feature === 'chat') {
      return (
        <>
          {pdfs.length === 0 && (
            <div
              className={`study-dropzone ${!isAuthenticated || uploading ? 'is-disabled' : ''}`}
              onClick={openFilePicker}
              onKeyDown={(e) => e.key === 'Enter' && openFilePicker()}
              role="button"
              tabIndex={0}
            >
              {uploading ? (
                <Loader2 className="icon icon--lg spin" />
              ) : (
                <Upload className="icon icon--lg icon--accent" />
              )}
              <p className="study-dropzone__text">
                {uploading ? 'Indexing your PDF…' : 'Drop a PDF here or click to upload'}
              </p>
              <p className="study-dropzone__hint">Text-based PDFs work best · First upload may take a minute</p>
            </div>
          )}
          <div className="study-main__messages">
            {messages.length === 0 && pdfs.length > 0 && (
              <div className="study-empty">
                <HelpCircle className="icon icon--xl icon--accent" />
                <p>Ask anything about your uploaded PDFs. Answers use Groq + RAG.</p>
              </div>
            )}
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`study-bubble study-bubble--${msg.role}${msg.error ? ' study-bubble--error' : ''}`}
              >
                <p>{msg.text}</p>
                {msg.sources?.length > 0 && (
                  <span className="study-bubble__sources">Sources: {msg.sources.join(', ')}</span>
                )}
              </div>
            ))}
            {busy && (
              <div className="study-bubble study-bubble--assistant study-bubble--typing">
                <Loader2 className="icon spin" /> Thinking…
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
          <form className="study-composer" onSubmit={handleAsk}>
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={
                selectedPdf
                  ? `Ask about ${truncate(selectedPdf, 28)}…`
                  : 'Ask across all your PDFs…'
              }
              disabled={!isAuthenticated || busy}
            />
            <button type="submit" disabled={!isAuthenticated || busy || !question.trim()}>
              <Send className="icon" />
            </button>
          </form>
        </>
      )
    }

    const isPdfFeature = ['notes', 'quiz', 'cards'].includes(feature)

    return (
      <div className="study-tool">
        <div className="study-tool__form">
          {isPdfFeature && (
            <>
              <p className="study-tool__intro">
                Content is taken from your uploaded PDF. Leave specification empty to use the{' '}
                <strong>entire</strong> selected document.
              </p>
              <label className="study-tool__label--full">
                Source PDF
                <select
                  value={toolPdf || ''}
                  onChange={(e) => setToolPdf(e.target.value || null)}
                  disabled={!pdfs.length}
                >
                  <option value="">All uploaded PDFs</option>
                  {pdfs.map((doc) => {
                    const name = doc.file_name || doc.filename
                    return (
                      <option key={doc.id || name} value={name}>
                        {name}
                      </option>
                    )
                  })}
                </select>
              </label>
              <label className="study-tool__label--full">
                Specification (optional)
                <textarea
                  value={specification}
                  onChange={(e) => setSpecification(e.target.value)}
                  placeholder="e.g. Chapter 4 — Backpropagation, pages 12–20, or ‘definitions and formulas only’"
                  rows={3}
                />
              </label>
              {(feature === 'quiz' || feature === 'cards') && (
                <label>
                  {feature === 'quiz' ? 'Number of questions' : 'Number of cards'}
                  <input
                    type="number"
                    min={3}
                    max={20}
                    value={numItems}
                    onChange={(e) => setNumItems(Number(e.target.value) || 5)}
                  />
                </label>
              )}
            </>
          )}
          {feature === 'roadmap' && (
            <label className="study-tool__label--full">
              Topic
              <input
                value={specification}
                onChange={(e) => setSpecification(e.target.value)}
                placeholder="e.g. Machine Learning fundamentals"
              />
            </label>
          )}
          {feature === 'plan' && (
            <>
              <label>
                Learning goal
                <input
                  value={planGoal}
                  onChange={(e) => setPlanGoal(e.target.value)}
                  placeholder="e.g. Pass AWS Solutions Architect exam"
                />
              </label>
              <label>
                Weeks
                <input
                  type="number"
                  min={1}
                  max={24}
                  value={planWeeks}
                  onChange={(e) => setPlanWeeks(Number(e.target.value) || 4)}
                />
              </label>
            </>
          )}
          <button
            type="button"
            className="study-btn-generate"
            onClick={runGenerator}
            disabled={!isAuthenticated || busy}
          >
            {busy ? <Loader2 className="icon spin" /> : <Sparkles className="icon" />}
            Generate
          </button>
        </div>
        <div className="study-tool__output">
          {output ? (
            <>
              {isPdfFeature && (
                <p className="study-tool__scope">
                  Generated from:{' '}
                  {specification.trim()
                    ? specification.trim()
                    : toolPdf
                      ? `Full PDF — ${toolPdf}`
                      : 'All uploaded PDFs'}
                </p>
              )}
              <pre>{output}</pre>
            </>
          ) : (
            <p className="study-tool__placeholder">
              {isPdfFeature
                ? 'Choose Notes, Quiz, or Flashcards, set an optional specification, then click Generate.'
                : 'Generated content appears here.'}
            </p>
          )}
        </div>
      </div>
    )
  }

  return (
    <Layout>
      <div className="study-page-v2">
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          className="study-file-input-hidden"
          onChange={handleUpload}
          aria-hidden
          tabIndex={-1}
        />

        <header className="study-page-v2__header">
          <span className="study-page-v2__badge">Groq · RAG · Chroma</span>
          <h1 className="study-page-v2__title">
            <BookOpen className="icon icon--lg icon--accent" />
            Study Assistant
          </h1>
          <p className="study-page-v2__subtitle">
            Upload PDFs · Ask questions · Notes · Quiz · Roadmaps
          </p>
        </header>

        {!authLoading && !isAuthenticated && (
          <div className="study-auth-banner">
            <Link to="/login">Sign in</Link> to upload PDFs and chat with your study materials.
          </div>
        )}

        <div className="study-app__grid">
          <aside className="study-sidebar">
            <div className="study-sidebar__brand">
              <BookOpen className="icon icon--accent" />
              <span>Study AI</span>
            </div>

            <button
              type="button"
              className="study-sidebar__new"
              onClick={handleNewChat}
              disabled={!isAuthenticated}
            >
              <MessageSquarePlus className="icon" />
              New chat
            </button>

            <button
              type="button"
              className={`study-sidebar__upload ${uploading ? 'is-busy' : ''} ${
                !isAuthenticated ? 'is-disabled' : ''
              }`}
              onClick={openFilePicker}
              disabled={uploading}
            >
              {uploading ? (
                <Loader2 className="icon spin" />
              ) : (
                <Upload className="icon" />
              )}
              <span>{uploading ? 'Indexing…' : 'Upload PDF'}</span>
            </button>

            <div className="study-sidebar__section">
              <h4 className="study-sidebar__heading">
                <FileText className="icon" /> Your PDFs
              </h4>
              <ul className="study-sidebar__list">
                {pdfs.length === 0 && (
                  <li className="study-sidebar__empty">No documents yet</li>
                )}
                {pdfs.map((doc) => {
                  const name = doc.file_name || doc.filename
                  return (
                    <li key={doc.id || name}>
                      <button
                        type="button"
                        className={`study-sidebar__item ${
                          selectedPdf === name ? 'study-sidebar__item--active' : ''
                        }`}
                        onClick={() => {
                          setSelectedPdf(name)
                          setFeature('chat')
                        }}
                      >
                        <FileText className="icon icon--sm" />
                        <span className="study-sidebar__item-text">
                          <span className="study-sidebar__item-title">{truncate(name, 22)}</span>
                          <span className="study-sidebar__item-meta">
                            {doc.total_chunks ?? 0} chunks
                          </span>
                        </span>
                      </button>
                      <button
                        type="button"
                        className="study-sidebar__item-del"
                        onClick={(e) => handleDeletePdf(name, e)}
                        aria-label="Delete PDF"
                      >
                        <Trash2 className="icon icon--sm" />
                      </button>
                    </li>
                  )
                })}
              </ul>
            </div>

            <div className="study-sidebar__section study-sidebar__section--grow">
              <h4 className="study-sidebar__heading">
                <HelpCircle className="icon" /> Chat history
              </h4>
              <ul className="study-sidebar__list study-sidebar__list--scroll">
                {chats.length === 0 && (
                  <li className="study-sidebar__empty">No chats yet</li>
                )}
                {chats.map((chat) => (
                  <li key={chat.id}>
                    <button
                      type="button"
                      className={`study-sidebar__item study-sidebar__item--chat ${
                        activeChatId === chat.id ? 'study-sidebar__item--active' : ''
                      }`}
                      onClick={() => handleSelectChat(chat)}
                    >
                      <span className="study-sidebar__item-text">
                        <span className="study-sidebar__item-title">
                          {truncate(chat.question)}
                        </span>
                        <span className="study-sidebar__item-meta">
                          {formatWhen(chat.asked_at)}
                          {chat.sources?.[0] ? ` · ${truncate(chat.sources[0], 14)}` : ''}
                        </span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>

            {savedPlans.length > 0 && (
              <div className="study-sidebar__section">
                <h4 className="study-sidebar__heading">
                  <Map className="icon" /> Saved plans
                </h4>
                <ul className="study-sidebar__list">
                  {savedPlans.slice(0, 6).map((p) => (
                    <li key={p.id}>
                      <button
                        type="button"
                        className="study-sidebar__item study-sidebar__item--chat"
                        onClick={() => {
                          setFeature(p.plan_type === 'study_plan' ? 'plan' : 'roadmap')
                          setOutput(p.content || '')
                        }}
                      >
                        <span className="study-sidebar__item-title">{truncate(p.topic, 28)}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </aside>

          <div className="study-main">
            <header className="study-main__header">
              <div className="study-features">
                {FEATURES.map((f) => (
                  <button
                    key={f.id}
                    type="button"
                    className={`study-features__btn ${
                      feature === f.id ? 'study-features__btn--active' : ''
                    }`}
                    onClick={() => {
                      setFeature(f.id)
                      if (f.id !== 'chat') setOutput('')
                    }}
                  >
                    <f.icon className="icon icon--sm" />
                    {f.label}
                  </button>
                ))}
              </div>
              {selectedPdf && feature === 'chat' && (
                <span className="study-main__context">
                  Context: <strong>{truncate(selectedPdf, 36)}</strong>
                </span>
              )}
            </header>
            <div className="study-main__body">{renderMain()}</div>
          </div>
        </div>
      </div>
    </Layout>
  )
}

export default StudyAssistant
