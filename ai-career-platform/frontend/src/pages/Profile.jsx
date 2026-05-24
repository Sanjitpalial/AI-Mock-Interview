import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'react-toastify'
import { motion } from 'framer-motion'
import { User, Save, Lock } from 'lucide-react'
import Layout from '../components/Layout'
import { useAuth } from '../context/AuthContext'
import { getProfile, updateProfile, changePassword } from '../api/client'
import './Profile.css'

const emptyForm = {
  name: '',
  phone: '',
  bio: '',
  headline: '',
  location: '',
  linkedin_url: '',
  github_url: '',
  portfolio_url: '',
  target_role: '',
  years_experience: '',
  education: '',
  skillsText: '',
}

export default function Profile() {
  const navigate = useNavigate()
  const { isAuthenticated, refreshUser, loading: authLoading } = useAuth()
  const [form, setForm] = useState(emptyForm)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [pw, setPw] = useState({ current: '', next: '', confirm: '' })
  const [pwSaving, setPwSaving] = useState(false)

  useEffect(() => {
    if (authLoading) return
    if (!isAuthenticated) {
      setLoading(false)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const p = await getProfile()
        if (!cancelled) {
          setForm({
            name: p.name || '',
            phone: p.phone || '',
            bio: p.bio || '',
            headline: p.headline || '',
            location: p.location || '',
            linkedin_url: p.linkedin_url || '',
            github_url: p.github_url || '',
            portfolio_url: p.portfolio_url || '',
            target_role: p.target_role || '',
            years_experience: p.years_experience || '',
            education: p.education || '',
            skillsText: (p.skills || []).join(', '),
          })
        }
      } catch (e) {
        if (!cancelled) toast.error(e.message || 'Could not load profile')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [isAuthenticated, authLoading])

  const onChange = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }))

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const skills = form.skillsText
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
      const updated = await updateProfile({
        name: form.name.trim(),
        phone: form.phone.trim() || null,
        bio: form.bio.trim() || null,
        headline: form.headline.trim() || null,
        location: form.location.trim() || null,
        linkedin_url: form.linkedin_url.trim() || null,
        github_url: form.github_url.trim() || null,
        portfolio_url: form.portfolio_url.trim() || null,
        target_role: form.target_role.trim() || null,
        years_experience: form.years_experience.trim() || null,
        education: form.education.trim() || null,
        skills,
      })
      await refreshUser()
      setForm((f) => ({
        ...f,
        skillsText: (updated.skills || []).join(', '),
      }))
      toast.success('Profile saved.')
    } catch (err) {
      toast.error(err.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const handlePassword = async (e) => {
    e.preventDefault()
    if (pw.next !== pw.confirm) {
      toast.error('New passwords do not match.')
      return
    }
    setPwSaving(true)
    try {
      await changePassword(pw.current, pw.next)
      setPw({ current: '', next: '', confirm: '' })
      toast.success('Password updated.')
    } catch (err) {
      toast.error(err.message || 'Password change failed')
    } finally {
      setPwSaving(false)
    }
  }

  if (!authLoading && !isAuthenticated) {
    return (
      <Layout>
        <main className="profile-page">
          <div className="container">
            <p>
              <Link to="/login">Sign in</Link> to manage your profile.
            </p>
          </div>
        </main>
      </Layout>
    )
  }

  return (
    <Layout>
      <main className="profile-page">
        <div className="container">
        <motion.header className="profile-page__header" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <User className="icon icon--accent" />
          <h1>Your profile</h1>
          <p>Update your info — used across mock interviews and your history.</p>
        </motion.header>

        {loading ? (
          <p className="profile-page__loading">Loading profile…</p>
        ) : (
          <form className="profile-form" onSubmit={handleSave}>
            <section className="profile-form__section">
              <h2>Basic</h2>
              <div className="profile-form__grid">
                <label>
                  Full name
                  <input value={form.name} onChange={onChange('name')} required />
                </label>
                <label>
                  Headline
                  <input value={form.headline} onChange={onChange('headline')} placeholder="e.g. ML Engineer @ …" />
                </label>
                <label>
                  Phone
                  <input value={form.phone} onChange={onChange('phone')} />
                </label>
                <label>
                  Location
                  <input value={form.location} onChange={onChange('location')} />
                </label>
                <label className="profile-form__full">
                  Bio
                  <textarea value={form.bio} onChange={onChange('bio')} rows={4} />
                </label>
              </div>
            </section>

            <section className="profile-form__section">
              <h2>Career</h2>
              <div className="profile-form__grid">
                <label>
                  Target role
                  <input value={form.target_role} onChange={onChange('target_role')} />
                </label>
                <label>
                  Years of experience
                  <input value={form.years_experience} onChange={onChange('years_experience')} placeholder="e.g. 3" />
                </label>
                <label className="profile-form__full">
                  Education
                  <textarea value={form.education} onChange={onChange('education')} rows={2} />
                </label>
                <label className="profile-form__full">
                  Skills (comma-separated)
                  <input value={form.skillsText} onChange={onChange('skillsText')} placeholder="Python, React, SQL" />
                </label>
              </div>
            </section>

            <section className="profile-form__section">
              <h2>Links</h2>
              <div className="profile-form__grid">
                <label>
                  LinkedIn
                  <input value={form.linkedin_url} onChange={onChange('linkedin_url')} type="url" />
                </label>
                <label>
                  GitHub
                  <input value={form.github_url} onChange={onChange('github_url')} type="url" />
                </label>
                <label className="profile-form__full">
                  Portfolio
                  <input value={form.portfolio_url} onChange={onChange('portfolio_url')} type="url" />
                </label>
              </div>
            </section>

            <button type="submit" className="btn btn--primary" disabled={saving}>
              <Save className="icon" />
              {saving ? 'Saving…' : 'Save profile'}
            </button>
          </form>
        )}

        <section className="profile-form__section profile-password">
          <h2>
            <Lock className="icon" /> Change password
          </h2>
          <form onSubmit={handlePassword} className="profile-form__grid">
            <label>
              Current password
              <input type="password" value={pw.current} onChange={(e) => setPw((p) => ({ ...p, current: e.target.value }))} />
            </label>
            <label>
              New password
              <input type="password" value={pw.next} onChange={(e) => setPw((p) => ({ ...p, next: e.target.value }))} />
            </label>
            <label>
              Confirm new password
              <input type="password" value={pw.confirm} onChange={(e) => setPw((p) => ({ ...p, confirm: e.target.value }))} />
            </label>
            <button type="submit" className="btn btn--secondary" disabled={pwSaving}>
              {pwSaving ? 'Updating…' : 'Update password'}
            </button>
          </form>
        </section>

        <p className="profile-page__footer">
          <button type="button" className="btn btn--ghost" onClick={() => navigate('/history')}>
            View interview history →
          </button>
        </p>
        </div>
      </main>
    </Layout>
  )
}
