/**
 * UI Slice - Manages UI state (toasts, modals, sidebar, etc.)
 */
import { createSlice } from '@reduxjs/toolkit'

let toastIdCounter = 0

const initialState = {
  // Sidebar
  sidebarCollapsed: localStorage.getItem('sidebarCollapsed') === 'true',
  sidebarMobileOpen: false,

  // Toasts
  toasts: [],

  // Modals
  modals: {
    confirmDelete: { open: false, data: null },
    createInstance: { open: false, data: null },
    instanceDetails: { open: false, data: null },
    settings: { open: false, data: null },
  },

  // Onboarding (UI state - actual completion in userSlice)
  showOnboarding: false,

  // Theme
  theme: localStorage.getItem('theme') || 'dark',

  // Loading overlays
  globalLoading: false,
  loadingMessage: '',

  // Provisioning race state
  provisioning: {
    active: false,
    candidates: [],
    winner: null,
  },
}

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    // Sidebar
    toggleSidebar: (state) => {
      state.sidebarCollapsed = !state.sidebarCollapsed
      localStorage.setItem('sidebarCollapsed', state.sidebarCollapsed)
    },
    setSidebarCollapsed: (state, action) => {
      state.sidebarCollapsed = action.payload
      localStorage.setItem('sidebarCollapsed', action.payload)
    },
    toggleMobileSidebar: (state) => {
      state.sidebarMobileOpen = !state.sidebarMobileOpen
    },
    closeMobileSidebar: (state) => {
      state.sidebarMobileOpen = false
    },

    // Toasts
    addToast: (state, action) => {
      const { message, type = 'info', duration = 4000 } = action.payload
      const id = ++toastIdCounter
      state.toasts.push({
        id,
        message,
        type,
        duration,
        createdAt: Date.now(),
      })
    },
    removeToast: (state, action) => {
      state.toasts = state.toasts.filter(t => t.id !== action.payload)
    },
    clearToasts: (state) => {
      state.toasts = []
    },

    // Modals
    openModal: (state, action) => {
      const { modal, data = null } = action.payload
      if (state.modals[modal]) {
        state.modals[modal] = { open: true, data }
      }
    },
    closeModal: (state, action) => {
      const modal = action.payload
      if (state.modals[modal]) {
        state.modals[modal] = { open: false, data: null }
      }
    },
    closeAllModals: (state) => {
      Object.keys(state.modals).forEach(key => {
        state.modals[key] = { open: false, data: null }
      })
    },

    // Onboarding
    setShowOnboarding: (state, action) => {
      state.showOnboarding = action.payload
    },

    // Theme
    setTheme: (state, action) => {
      state.theme = action.payload
      localStorage.setItem('theme', action.payload)
      document.documentElement.classList.toggle('dark', action.payload === 'dark')
    },
    toggleTheme: (state) => {
      state.theme = state.theme === 'dark' ? 'light' : 'dark'
      localStorage.setItem('theme', state.theme)
      document.documentElement.classList.toggle('dark', state.theme === 'dark')
    },

    // Global loading
    setGlobalLoading: (state, action) => {
      if (typeof action.payload === 'boolean') {
        state.globalLoading = action.payload
        state.loadingMessage = ''
      } else {
        state.globalLoading = action.payload.loading
        state.loadingMessage = action.payload.message || ''
      }
    },

    // Provisioning race
    startProvisioning: (state, action) => {
      state.provisioning = {
        active: true,
        candidates: action.payload.map((offer, index) => ({
          ...offer,
          status: 'connecting',
          progress: 0,
          connectionTime: Math.random() * 5000 + 2000,
        })),
        winner: null,
      }
    },
    updateProvisioningCandidate: (state, action) => {
      const { index, updates } = action.payload
      if (state.provisioning.candidates[index]) {
        state.provisioning.candidates[index] = {
          ...state.provisioning.candidates[index],
          ...updates,
        }
      }
    },
    setProvisioningWinner: (state, action) => {
      state.provisioning.winner = action.payload
    },
    endProvisioning: (state) => {
      state.provisioning = {
        active: false,
        candidates: [],
        winner: null,
      }
    },
  },
})

export const {
  toggleSidebar,
  setSidebarCollapsed,
  toggleMobileSidebar,
  closeMobileSidebar,
  addToast,
  removeToast,
  clearToasts,
  openModal,
  closeModal,
  closeAllModals,
  setShowOnboarding,
  setTheme,
  toggleTheme,
  setGlobalLoading,
  startProvisioning,
  updateProvisioningCandidate,
  setProvisioningWinner,
  endProvisioning,
} = uiSlice.actions

// Selectors
export const selectSidebarCollapsed = (state) => state.ui.sidebarCollapsed
export const selectMobileSidebarOpen = (state) => state.ui.sidebarMobileOpen
export const selectToasts = (state) => state.ui.toasts
export const selectModal = (modal) => (state) => state.ui.modals[modal]
export const selectShowOnboarding = (state) => state.ui.showOnboarding
export const selectTheme = (state) => state.ui.theme
export const selectGlobalLoading = (state) => state.ui.globalLoading
export const selectLoadingMessage = (state) => state.ui.loadingMessage
export const selectProvisioning = (state) => state.ui.provisioning

export default uiSlice.reducer
