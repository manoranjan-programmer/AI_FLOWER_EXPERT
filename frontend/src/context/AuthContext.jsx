/**
 * AuthContext.jsx
 * Central Authentication Context for Flower AI Expert.
 * Manages Google Sign-In authentication state, user session restoration, and logout.
 */

import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { loginWithGoogleApi, fetchCurrentUserApi, logoutApi } from '../api/flowerApi'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem('flower_ai_user')
      return saved ? JSON.parse(saved) : null
    } catch (e) {
      return null
    }
  })
  const [isAuthLoading, setIsAuthLoading] = useState(true)
  const [authError, setAuthError] = useState(null)

  // Auto-restore active session on application mount
  useEffect(() => {
    let isMounted = true
    async function restoreSession() {
      try {
        const data = await fetchCurrentUserApi()
        if (isMounted && data && data.user) {
          setUser(data.user)
          localStorage.setItem('flower_ai_user', JSON.stringify(data.user))
        }
      } catch (err) {
        // If cookie check fails, keep local backup if valid or set null
        if (isMounted) {
          logger_debug('No active HTTP-only session cookie found.')
        }
      } finally {
        if (isMounted) {
          setIsAuthLoading(false)
        }
      }
    }
    restoreSession()
    return () => {
      isMounted = false
    }
  }, [])

  function logger_debug(msg) {
    if (import.meta.env.DEV) {
      console.debug('[AuthContext]', msg)
    }
  }

  // Handle Google OAuth Credential Login
  const loginWithGoogle = useCallback(async (credential) => {
    setIsAuthLoading(true)
    setAuthError(null)
    try {
      const data = await loginWithGoogleApi(credential)
      if (data && data.user) {
        setUser(data.user)
        localStorage.setItem('flower_ai_user', JSON.stringify(data.user))
        return data.user
      }
      throw new Error('Could not retrieve user profile from backend.')
    } catch (err) {
      const errorMsg = err.message || 'Google authentication failed.'
      setAuthError(errorMsg)
      throw new Error(errorMsg)
    } finally {
      setIsAuthLoading(false)
    }
  }, [])

  // Instant Demo Login (for local dev / testing before live Google OAuth Client ID is set)
  const demoLogin = useCallback(async (customUser = null) => {
    setIsAuthLoading(true)
    const demoProfile = customUser || {
      id: 'usr_demo_1001',
      google_id: '109823471092834710',
      name: 'Botanist Scholar',
      email: 'botanist.expert@flowerai.com',
      picture: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=256&q=80',
      role: 'botanist',
      created_at: new Date().toISOString(),
      login_timestamp: new Date().toISOString(),
    }
    try {
      // Simulate credential string
      const fakeCredential = window.btoa(JSON.stringify(demoProfile))
      const data = await loginWithGoogleApi(fakeCredential)
      if (data && data.user) {
        setUser(data.user)
        localStorage.setItem('flower_ai_user', JSON.stringify(data.user))
        return data.user
      }
      setUser(demoProfile)
      localStorage.setItem('flower_ai_user', JSON.stringify(demoProfile))
      return demoProfile
    } catch (err) {
      setUser(demoProfile)
      localStorage.setItem('flower_ai_user', JSON.stringify(demoProfile))
      return demoProfile
    } finally {
      setIsAuthLoading(false)
    }
  }, [])

  // Handle User Logout
  const logout = useCallback(async () => {
    setIsAuthLoading(true)
    try {
      await logoutApi()
    } catch (err) {
      console.warn('Logout endpoint warning:', err)
    } finally {
      setUser(null)
      localStorage.removeItem('flower_ai_user')
      setIsAuthLoading(false)
    }
  }, [])

  const value = {
    user,
    isAuthenticated: Boolean(user),
    isAuthLoading,
    authError,
    loginWithGoogle,
    demoLogin,
    logout,
    setAuthError,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}

export default AuthContext
