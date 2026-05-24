import { useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Brain,
  Mic,
  BookOpen,
  BarChart3,
  ArrowRight,
  CheckCircle,
  TrendingUp,
  FileText,
  Target,
  Play,
} from 'lucide-react'
import Layout from '../components/Layout'
import './Home.css'

const features = [
  {
    icon: Mic,
    title: 'AI Mock Interviews',
    description:
      'Resume-based questions with real-time voice/text responses. Get scored by our Evaluation Agent with semantic similarity analysis.',
  },
  {
    icon: BookOpen,
    title: 'RAG Study Assistant',
    description:
      'Upload PDFs and get AI-generated notes, quizzes, and personalized study roadmaps powered by vector search and LangChain.',
  },
  {
    icon: Brain,
    title: 'LangGraph Agents',
    description:
      'Multi-agent orchestration with Resume Analyzer, Interview, Evaluation, Communication, and Study Planner agents.',
  },
  {
    icon: BarChart3,
    title: 'SAS Analytics',
    description:
      'Predictive intelligence using PROC REG, PROC LOGISTIC, PROC FASTCLUS, and PROC ARIMA for interview readiness forecasting.',
  },
  {
    icon: Target,
    title: 'Company-Specific Prep',
    description:
      'Tailored interview questions and preparation strategies for FAANG, startups, and domain-specific companies.',
  },
  {
    icon: TrendingUp,
    title: 'Predictive Readiness',
    description:
      'SAS-powered percentile analysis, candidate clustering, and trend forecasting with downloadable ODS PDF reports.',
  },
]

const workflowSteps = [
  {
    step: '01',
    title: 'Upload Resume',
    desc: 'Resume Analyzer Agent parses and embeds your resume into ChromaDB vector store',
    icon: FileText,
  },
  {
    step: '02',
    title: 'AI Interview',
    desc: 'Interview Agent generates personalized questions. Answer via text or voice (Whisper API)',
    icon: Mic,
  },
  {
    step: '03',
    title: 'Evaluation & Scoring',
    desc: 'Evaluation Agent scores responses using semantic similarity, confidence, and sentiment analysis',
    icon: CheckCircle,
  },
  {
    step: '04',
    title: 'SAS Analytics',
    desc: 'Data flows to SAS for PROC REG readiness prediction, PROC FASTCLUS clustering, and PROC ARIMA forecasting',
    icon: BarChart3,
  },
  {
    step: '05',
    title: 'Insights Dashboard',
    desc: 'Combined AI + SAS reports with downloadable ODS PDF analytics and personalized improvement roadmap',
    icon: TrendingUp,
  },
]

const Home = () => {
  const navigate = useNavigate()
  const location = useLocation()

  const scrollToHowItWorks = () => {
    document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    if (location.state?.scrollTo === 'how-it-works') {
      scrollToHowItWorks()
      window.history.replaceState({}, document.title)
    }
  }, [location.state])

  return (
    <Layout>
      <div className="page-home">

        {/* ── HERO ── */}
        <section className="landing-hero">
          <div className="landing-hero__bg" aria-hidden="true" />
          <div className="landing-hero__inner">
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <h1 className="landing-hero__title">
                Ace every interview with{' '}
                <span className="landing-hero__title-accent">agentic AI.</span>
              </h1>

              <p className="landing-hero__desc">
                The most advanced career preparation platform combining multi-agent LangGraph workflows, RAG-powered study assistance, and SAS predictive analytics to maximize your interview success rate.
              </p>

              <div className="landing-hero__actions">
                <button
                  type="button"
                  className="btn btn--lg btn--primary"
                  onClick={() => navigate('/interview')}
                >
                  <Play className="icon icon--sm" />
                  Start Mock Interview
                </button>
                <button
                  type="button"
                  className="btn btn--lg btn--secondary"
                  onClick={scrollToHowItWorks}
                >
                  <BookOpen className="icon icon--sm" />
                  View How It Works
                </button>
              </div>
            </motion.div>
          </div>
        </section>

        {/* ── FEATURES ── */}
        <section className="landing-section landing-section--alt">
          <div className="landing-section__header">
            <h2 className="landing-section__title">
              Everything you need to{' '}
              <span className="landing-hero__title-accent" style={{ fontStyle: 'italic' }}>land the job.</span>
            </h2>
            <p className="landing-section__subtitle">
              Six integrated systems working together to give you the most comprehensive career preparation experience available.
            </p>
          </div>

          <div className="landing-features">
            {features.map((feature, i) => (
              <motion.div
                key={feature.title}
                className="landing-feature-card"
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.06 }}
              >
                <feature.icon className="icon icon--lg landing-feature-card__icon" />
                <h3 className="landing-feature-card__title">{feature.title}</h3>
                <p className="landing-feature-card__desc">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </section>

        {/* ── HOW IT WORKS ── */}
        <section id="how-it-works" className="landing-section">
          <div className="landing-section__header">
            <h2 className="landing-section__title">How it works.</h2>
            <p className="landing-section__subtitle">From resume upload to predictive analytics in minutes.</p>
          </div>

          <div className="landing-workflow">
            {workflowSteps.map((item, i) => (
              <motion.div
                key={item.step}
                className="landing-workflow__item"
                initial={{ opacity: 0, x: -12 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.08 }}
              >
                <div className="landing-workflow__icon-wrap">
                  <item.icon className="icon" />
                </div>
                <div>
                  <div className="landing-workflow__step">{item.step}</div>
                  <h3 className="landing-workflow__title">{item.title}</h3>
                  <p className="landing-workflow__desc">{item.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </section>

        {/* ── CTA ── */}
        <section className="landing-section landing-section--alt">
          <div className="landing-cta">
            <motion.div
              className="landing-cta__box"
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
            >
              <div className="landing-cta__icon">
                <Brain className="icon icon--lg icon--on-accent" />
              </div>
              <h2 className="landing-cta__title">Ready to transform your career?</h2>
              <p className="landing-cta__desc">
                Join thousands of candidates who use CareerAI&apos;s agentic platform to land their dream roles at top companies.
              </p>
              <div className="landing-cta__actions">
                <Link to="/interview" className="btn btn--primary btn--lg">
                  Start Free Interview <ArrowRight className="icon" />
                </Link>
                <Link to="/study" className="btn btn--secondary btn--lg">
                  Explore Study Assistant
                </Link>
              </div>
            </motion.div>
          </div>
        </section>

      </div>
    </Layout>
  )
}

export default Home