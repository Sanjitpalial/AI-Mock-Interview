import { Link } from 'react-router-dom'
import { BrainCircuit } from 'lucide-react'

import './Footer.css'

const Footer = () => {
  return (
    <footer className="footer">
      <div className="footer__inner">
        <div className="footer__grid">
          <div>
            <Link to="/" className="footer__brand">
              <div className="navbar__logo">
                <BrainCircuit className="icon icon--sm icon--on-accent" />
              </div>
              <span className="navbar__title">CareerAI</span>
            </Link>
            <p className="footer__desc">
              AI-powered career preparation with LangGraph multi-agent interviews and SAS predictive analytics.
            </p>
          </div>
          <div>
            <h4 className="footer__heading">Product</h4>
            <ul className="footer__links">
              <li><Link to="/interview">Mock Interview</Link></li>
              <li><Link to="/study">Study Assistant</Link></li>
              <li><Link to="/analytics">Analytics</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="footer__heading">Account</h4>
            <ul className="footer__links">
              <li><Link to="/login">Sign In</Link></li>
              <li><Link to="/register">Register</Link></li>
            </ul>
          </div>
        </div>
        <p className="footer__copy">
          © {new Date().getFullYear()} CareerAI. LangGraph · RAG · SAS Analytics.
        </p>
      </div>
    </footer>
  )
}

export default Footer
