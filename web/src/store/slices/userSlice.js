/**
 * User Slice - Manages user profile and settings
 */
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'

const API_BASE = import.meta.env.VITE_API_URL || ''

const getToken = () => localStorage.getItem('auth_token')

// Async thunks
export const fetchUser = createAsyncThunk(
  'user/fetchUser',
  async (_, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok || !data.authenticated) {
        return rejectWithValue('Failed to fetch user')
      }
      return data.user
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const updateSettings = createAsyncThunk(
  'user/updateSettings',
  async (settings, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/settings`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ settings }),
      })
      if (!res.ok) {
        return rejectWithValue('Failed to update settings')
      }
      return settings
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const completeOnboarding = createAsyncThunk(
  'user/completeOnboarding',
  async (_, { rejectWithValue }) => {
    try {
      // Mark in localStorage immediately
      localStorage.setItem('onboarding_completed', 'true')

      const res = await fetch(`${API_BASE}/api/v1/settings/complete-onboarding`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      if (!res.ok) {
        console.error('Failed to complete onboarding on server')
      }
      return true
    } catch (error) {
      console.error('Error completing onboarding:', error)
      return true // Still mark as completed locally
    }
  }
)

export const fetchBalance = createAsyncThunk(
  'user/fetchBalance',
  async (_, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/balance`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue('Failed to fetch balance')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

const initialState = {
  user: null,
  settings: {},
  balance: {
    credit: 0,
    balance: 0,
  },
  hasCompletedOnboarding: localStorage.getItem('onboarding_completed') === 'true',
  loading: false,
  error: null,
}

const userSlice = createSlice({
  name: 'user',
  initialState,
  reducers: {
    clearUser: (state) => {
      state.user = null
      state.settings = {}
      state.hasCompletedOnboarding = false
    },
    setOnboardingCompleted: (state, action) => {
      state.hasCompletedOnboarding = action.payload
      if (action.payload) {
        localStorage.setItem('onboarding_completed', 'true')
      } else {
        localStorage.removeItem('onboarding_completed')
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch User
      .addCase(fetchUser.pending, (state) => {
        state.loading = true
      })
      .addCase(fetchUser.fulfilled, (state, action) => {
        state.loading = false
        state.user = action.payload
        state.settings = action.payload?.settings || {}
        // Sync onboarding status
        if (action.payload?.settings?.has_completed_onboarding) {
          state.hasCompletedOnboarding = true
          localStorage.setItem('onboarding_completed', 'true')
        }
      })
      .addCase(fetchUser.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Update Settings
      .addCase(updateSettings.fulfilled, (state, action) => {
        state.settings = { ...state.settings, ...action.payload }
      })
      // Complete Onboarding
      .addCase(completeOnboarding.fulfilled, (state) => {
        state.hasCompletedOnboarding = true
        state.settings = { ...state.settings, has_completed_onboarding: true }
      })
      // Fetch Balance
      .addCase(fetchBalance.fulfilled, (state, action) => {
        state.balance = action.payload
      })
  },
})

export const { clearUser, setOnboardingCompleted } = userSlice.actions

// Selectors
export const selectUser = (state) => state.user.user
export const selectUserSettings = (state) => state.user.settings
export const selectUserBalance = (state) => state.user.balance
export const selectHasCompletedOnboarding = (state) => state.user.hasCompletedOnboarding
export const selectUserLoading = (state) => state.user.loading
export const selectUserEmail = (state) => state.user.user?.email || state.user.user?.username

export default userSlice.reducer
