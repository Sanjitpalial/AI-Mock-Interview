import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'react-toastify'
import { BrainCircuit, ArrowLeft } from 'lucide-react'

import { registerRequest, loginRequest } from '../api/client'
import { useAuth } from '../context/AuthContext'
import './Register.css'

export default function Register() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!name.trim() || !email.trim() || !password) {
      toast.error('Fill in all fields.')
      return
    }
    if (password.length < 6) {
      toast.error('Use a password with at least 6 characters.')
      return
    }
    setLoading(true)
    try {
      const user = await registerRequest(name.trim(), email.trim(), password)
      const auth = await loginRequest(email.trim(), password)
      await login(auth.access_token, user)
      toast.success(`Welcome, ${user.name}!`)
      navigate('/interview')
    } catch (err) {
      toast.error(err.message || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="register-page">
      <Link to="/" className="register-page__back">
        <ArrowLeft className="icon" /> Back to Home
      </Link>
      <div className="register-card">
        <div className="register-card__header">
          <div className="register-card__logo">
            <BrainCircuit className="icon icon--lg icon--on-accent" />
          </div>
          <h1 className="register-card__title">Create Account</h1>
          <p className="register-card__subtitle">Start your AI-powered career journey</p>
        </div>
        <form className="form" onSubmit={handleSubmit}>
          <div className="form__group">
            <label className="form__label">Full Name</label>
            <input
              type="text"
              className="form__input"
              placeholder="John Doe"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoComplete="name"
            />
          </div>
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
              autoComplete="new-password"
            />
          </div>
          <button type="submit" className="btn btn--primary btn--full" disabled={loading}>
            {loading ? 'Creating…' : 'Get Started'}
          </button>
        </form>
        <p className="register-card__footer">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
