import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import {
  getToken,
  setToken as saveToken,
  clearToken,
  getStoredUser,
  setStoredUser,
  getProfile,
} from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => getStoredUser())
  const [loading, setLoading] = useState(!!getToken())

  const refreshUser = useCallback(async () => {
    const token = getToken()
    if (!token) {
      setUser(null)
      setStoredUser(null)
      setLoading(false)
      return
    }
    try {
      const me = await getProfile()
      setUser(me)
      setStoredUser(me)
    } catch {
      clearToken()
      setUser(null)
      setStoredUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refreshUser()
  }, [refreshUser])

  const login = useCallback(async (token, profile = null) => {
    saveToken(token)
    if (profile) {
      setUser(profile)
      setStoredUser(profile)
      setLoading(false)
      return
    }
    setLoading(true)
    await refreshUser()
  }, [refreshUser])

  const logout = useCallback(() => {
    clearToken()
    setUser(null)
    setStoredUser(null)
  }, [])

  const value = {
    user,
    loading,
    isAuthenticated: !!user && !!getToken(),
    login,
    logout,
    refreshUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return ctx
}
