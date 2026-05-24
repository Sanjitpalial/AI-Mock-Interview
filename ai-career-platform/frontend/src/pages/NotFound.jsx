import { Link } from 'react-router-dom'
import { Home, BrainCircuit } from 'lucide-react'

import './NotFound.css'

export default function NotFound() {
  return (
    <div className="not-found-page">
      <div className="not-found-page__icon-wrap">
        <BrainCircuit className="icon icon--xl icon--accent" />
      </div>
      <h1 className="not-found-page__code">404</h1>
      <p className="not-found-page__text">This page doesn&apos;t exist. Let&apos;s get you back on track.</p>
      <Link to="/" className="btn btn--primary">
        <Home className="icon" /> Back to Home
      </Link>
    </div>
  )
}
