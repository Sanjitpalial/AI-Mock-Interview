import { useState, useEffect, useRef } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Menu, X, BrainCircuit, User, LogOut, ChevronDown, History } from 'lucide-react'

import { useAuth } from '../context/AuthContext'
import './Navbar.css'

const Navbar = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const { user, isAuthenticated, logout, loading } = useAuth()
  const userMenuRef = useRef(null)

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  useEffect(() => {
    setUserMenuOpen(false)
    setIsOpen(false)
  }, [location.pathname])

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) {
        setUserMenuOpen(false)
      }
    }
    if (userMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [userMenuOpen])

  const navLinks = [
    { name: 'Mock Interview', path: '/interview' },
    { name: 'Study Assistant', path: '/study' },
    { name: 'Analytics', path: '/analytics' },
  ]

  const isActive = (path) => location.pathname === path

  const handleLogout = () => {
    logout()
    setUserMenuOpen(false)
    setIsOpen(false)
    navigate('/')
  }

  const displayName = user?.name?.trim() || user?.email?.split('@')[0] || 'Account'

  return (
    <header className={`navbar ${scrolled ? 'navbar--scrolled' : ''}`}>
      <nav className="navbar__inner">
        <Link to="/" className="navbar__brand">
          <div className="navbar__logo">
            <BrainCircuit className="icon icon--on-accent" />
          </div>
          <span className="navbar__title">CareerAI</span>
        </Link>

        <div className="navbar__links">
          {navLinks.map((link) => (
            <Link
              key={link.path}
              to={link.path}
              className={`navbar__link ${isActive(link.path) ? 'navbar__link--active' : ''}`}
            >
              {link.name}
              {isActive(link.path) && (
                <motion.div layoutId="nav-underline" className="navbar__link-underline" />
              )}
            </Link>
          ))}
        </div>

        <div className="navbar__actions">
          {loading ? (
            <span className="navbar__user-label">…</span>
          ) : isAuthenticated ? (
            <>
              <div className="navbar__user-menu" ref={userMenuRef}>
                <button
                  type="button"
                  className={`navbar__user-pill ${userMenuOpen ? 'navbar__user-pill--open' : ''}`}
                  onClick={() => setUserMenuOpen((o) => !o)}
                  aria-expanded={userMenuOpen}
                  aria-haspopup="true"
                >
                  <User className="icon icon--sm" />
                  <span className="navbar__user-pill-text">{displayName}</span>
                  <ChevronDown className={`icon icon--sm navbar__chevron ${userMenuOpen ? 'navbar__chevron--open' : ''}`} />
                </button>
                <AnimatePresence>
                  {userMenuOpen && (
                    <motion.div
                      className="navbar__dropdown"
                      initial={{ opacity: 0, y: -6 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -6 }}
                      transition={{ duration: 0.15 }}
                    >
                      <p className="navbar__dropdown-email">{user?.email}</p>
                      <Link to="/profile" className="navbar__dropdown-item" onClick={() => setUserMenuOpen(false)}>
                        <User className="icon icon--sm" />
                        Profile
                      </Link>
                      <Link to="/history" className="navbar__dropdown-item" onClick={() => setUserMenuOpen(false)}>
                        <History className="icon icon--sm" />
                        History
                      </Link>
                      <hr className="navbar__dropdown-divider" />
                      <button type="button" className="navbar__dropdown-item navbar__dropdown-item--danger" onClick={handleLogout}>
                        <LogOut className="icon icon--sm" />
                        Log out
                      </button>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </>
          ) : (
            <>
              <Link to="/login" className="btn btn--ghost">
                Sign In
              </Link>
              <Link to="/register" className="btn btn--primary">
                Get Started
              </Link>
            </>
          )}
        </div>

        <button
          type="button"
          className="navbar__menu-btn"
          onClick={() => setIsOpen(!isOpen)}
          aria-label="Toggle menu"
        >
          {isOpen ? <X className="icon" /> : <Menu className="icon" />}
        </button>
      </nav>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="navbar__mobile"
          >
            <div className="navbar__mobile-inner">
              {navLinks.map((link) => (
                <Link
                  key={link.path}
                  to={link.path}
                  onClick={() => setIsOpen(false)}
                  className={`navbar__mobile-link ${isActive(link.path) ? 'navbar__mobile-link--active' : ''}`}
                >
                  {link.name}
                </Link>
              ))}
              <hr className="navbar__mobile-divider" />
              {isAuthenticated ? (
                <>
                  <p className="navbar__mobile-user">
                    <User className="icon icon--sm" />
                    {displayName}
                  </p>
                  <Link to="/profile" onClick={() => setIsOpen(false)} className="navbar__mobile-link">
                    Profile
                  </Link>
                  <Link to="/history" onClick={() => setIsOpen(false)} className="navbar__mobile-link">
                    History
                  </Link>
                  <button type="button" onClick={handleLogout} className="navbar__mobile-action">
                    <LogOut className="icon icon--sm" /> Log out
                  </button>
                </>
              ) : (
                <>
                  <Link to="/login" onClick={() => setIsOpen(false)} className="navbar__mobile-action">
                    Sign In
                  </Link>
                  <Link
                    to="/register"
                    onClick={() => setIsOpen(false)}
                    className="navbar__mobile-action navbar__mobile-action--accent"
                  >
                    Get Started
                  </Link>
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  )
}

export default Navbar
