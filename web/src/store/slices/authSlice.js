/**
 * Auth Slice - Manages authentication state
 */
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'

const API_BASE = import.meta.env.VITE_API_URL || ''

// Async thunks
export const login = createAsyncThunk(
  'auth/login',
  async ({ email, password }, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Falha no login')
      }
      // Store token
      localStorage.setItem('auth_token', data.token)
      return data
    } catch (error) {
      return rejectWithValue(error.message || 'Erro de conexão')
    }
  }
)

export const register = createAsyncThunk(
  'auth/register',
  async ({ email, password, username }, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, username }),
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Falha no registro')
      }
      // Store token
      localStorage.setItem('auth_token', data.token)
      return data
    } catch (error) {
      return rejectWithValue(error.message || 'Erro de conexão')
    }
  }
)

export const checkAuth = createAsyncThunk(
  'auth/checkAuth',
  async (_, { rejectWithValue }) => {
    try {
      const token = localStorage.getItem('auth_token')
      if (!token) {
        return rejectWithValue('No token')
      }
      const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` },
      })
      const data = await res.json()
      if (!res.ok || !data.authenticated) {
        localStorage.removeItem('auth_token')
        return rejectWithValue('Invalid token')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const logout = createAsyncThunk(
  'auth/logout',
  async (_, { rejectWithValue }) => {
    try {
      const token = localStorage.getItem('auth_token')
      await fetch(`${API_BASE}/api/v1/auth/logout`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      })
      localStorage.removeItem('auth_token')
      localStorage.removeItem('onboarding_completed')
      return null
    } catch (error) {
      // Still logout locally even if API fails
      localStorage.removeItem('auth_token')
      localStorage.removeItem('onboarding_completed')
      return null
    }
  }
)

const initialState = {
  isAuthenticated: false,
  token: localStorage.getItem('auth_token') || null,
  loading: false,
  error: null,
  initialized: false,
}

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null
    },
    setToken: (state, action) => {
      state.token = action.payload
      state.isAuthenticated = !!action.payload
      if (action.payload) {
        localStorage.setItem('auth_token', action.payload)
      } else {
        localStorage.removeItem('auth_token')
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Login
      .addCase(login.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(login.fulfilled, (state, action) => {
        state.loading = false
        state.isAuthenticated = true
        state.token = action.payload.token
        state.error = null
      })
      .addCase(login.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Register
      .addCase(register.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(register.fulfilled, (state, action) => {
        state.loading = false
        state.isAuthenticated = true
        state.token = action.payload.token
        state.error = null
      })
      .addCase(register.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Check Auth
      .addCase(checkAuth.pending, (state) => {
        state.loading = true
      })
      .addCase(checkAuth.fulfilled, (state, action) => {
        state.loading = false
        state.isAuthenticated = true
        state.initialized = true
      })
      .addCase(checkAuth.rejected, (state) => {
        state.loading = false
        state.isAuthenticated = false
        state.token = null
        state.initialized = true
      })
      // Logout
      .addCase(logout.fulfilled, (state) => {
        state.isAuthenticated = false
        state.token = null
        state.error = null
      })
  },
})

export const { clearError, setToken } = authSlice.actions

// Selectors
export const selectIsAuthenticated = (state) => state.auth.isAuthenticated
export const selectAuthLoading = (state) => state.auth.loading
export const selectAuthError = (state) => state.auth.error
export const selectAuthInitialized = (state) => state.auth.initialized
export const selectToken = (state) => state.auth.token

export default authSlice.reducer
