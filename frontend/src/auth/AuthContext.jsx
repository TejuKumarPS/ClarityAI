import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { apiClient } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(() => apiClient.getToken())
  const [loading, setLoading] = useState(true)

  const logout = useCallback(() => {
    apiClient.setToken(null)
    setToken(null)
    setUser(null)
  }, [])

  const refreshUser = useCallback(async () => {
    const currentToken = apiClient.getToken()
    if (!currentToken) {
      setUser(null)
      setLoading(false)
      return null
    }

    try {
      const userData = await apiClient.getCurrentUser()
      setUser(userData)
      setToken(currentToken)
      return userData
    } catch {
      logout()
      return null
    } finally {
      setLoading(false)
    }
  }, [logout])

  useEffect(() => {
    apiClient.setOnUnauthorized(logout)
    refreshUser()
  }, [logout, refreshUser])

  const login = async (email, password) => {
    const loginData = await apiClient.login(email, password)
    const activeToken = loginData.access_token
    setToken(activeToken)
    const userData = await apiClient.getCurrentUser()
    setUser(userData)
    return userData
  }

  const register = async (email, password) => {
    await apiClient.register(email, password)
    // Auto-login upon successful registration
    return login(email, password)
  }

  const value = {
    user,
    token,
    loading,
    isAuthenticated: Boolean(user && token),
    login,
    register,
    logout,
    refreshUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
