import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'react-toastify'
import { BrainCircuit, ArrowLeft } from 'lucide-react'

import { loginRequest } from '../api/client'
import { useAuth } from '../context/AuthContext'
import './Login.css'

export default function Login() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!email.trim() || !password) {
      toast.error('Enter email and password.')
      return
    }
    setLoading(true)
    try {
      const data = await loginRequest(email.trim(), password)
      await login(data.access_token)
      toast.success('Signed in.')
      navigate('/interview')
    } catch (err) {
      toast.error(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <Link to="/" className="login-page__back">
        <ArrowLeft className="icon" /> Back to Home
      </Link>
      <div className="login-card">
        <div className="login-card__header">
          <div className="login-card__logo">
            <BrainCircuit className="icon icon--lg icon--on-accent" />
          </div>
          <h1 className="login-card__title">Welcome Back</h1>
          <p className="login-card__subtitle">Sign in to continue your preparation</p>
        </div>
        <form className="form" onSubmit={handleSubmit}>
          <div className="form__group">
            <label className="form__label">Email Address</label>
            <input
              type="email"
              className="form__input"
              placeholder="name@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
            />
          </div>
          <div className="form__group">
            <label className="form__label">Password</label>
            <input
              type="password"
              className="form__input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>
          <button type="submit" className="btn btn--primary btn--full" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>
        <p className="login-card__footer">
          Don&apos;t have an account? <Link to="/register">Create one</Link>
        </p>
      </div>
    </div>
  )
}
