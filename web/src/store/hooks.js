/**
 * Custom Redux Hooks
 * Type-safe hooks for use throughout the app
 */
import { useDispatch, useSelector } from 'react-redux'
import { useCallback, useEffect } from 'react'
import { addToast, removeToast } from './slices/uiSlice'
import { fetchInstances, fetchOffers } from './slices/instancesSlice'
import { fetchUser, completeOnboarding } from './slices/userSlice'
import { checkAuth, logout } from './slices/authSlice'

// Re-export typed hooks
export const useAppDispatch = useDispatch
export const useAppSelector = useSelector

/**
 * Toast hook - easy toast notifications
 */
export const useToastRedux = () => {
  const dispatch = useDispatch()
  const toasts = useSelector(state => state.ui.toasts)

  const toast = useCallback((message, type = 'info', duration = 4000) => {
    dispatch(addToast({ message, type, duration }))
  }, [dispatch])

  const success = useCallback((message, duration) => toast(message, 'success', duration), [toast])
  const error = useCallback((message, duration) => toast(message, 'error', duration), [toast])
  const warning = useCallback((message, duration) => toast(message, 'warning', duration), [toast])
  const info = useCallback((message, duration) => toast(message, 'info', duration), [toast])

  const remove = useCallback((id) => {
    dispatch(removeToast(id))
  }, [dispatch])

  return { toast, success, error, warning, info, remove, toasts }
}

/**
 * Auth hook - authentication state and actions
 */
export const useAuth = () => {
  const dispatch = useDispatch()
  const { isAuthenticated, loading, error, initialized, token } = useSelector(state => state.auth)

  const check = useCallback(() => {
    return dispatch(checkAuth())
  }, [dispatch])

  const logoutUser = useCallback(() => {
    return dispatch(logout())
  }, [dispatch])

  return {
    isAuthenticated,
    loading,
    error,
    initialized,
    token,
    check,
    logout: logoutUser,
  }
}

/**
 * User hook - user profile and settings
 */
export const useUser = () => {
  const dispatch = useDispatch()
  const { user, settings, balance, hasCompletedOnboarding, loading } = useSelector(state => state.user)

  const fetch = useCallback(() => {
    return dispatch(fetchUser())
  }, [dispatch])

  const finishOnboarding = useCallback(() => {
    return dispatch(completeOnboarding())
  }, [dispatch])

  return {
    user,
    settings,
    balance,
    hasCompletedOnboarding,
    loading,
    fetch,
    completeOnboarding: finishOnboarding,
  }
}

/**
 * Instances hook - GPU instances management
 */
export const useInstances = () => {
  const dispatch = useDispatch()
  const {
    instances,
    offers,
    selectedOffer,
    stats,
    filters,
    loading,
    offersLoading,
    error,
  } = useSelector(state => state.instances)

  const fetch = useCallback(() => {
    return dispatch(fetchInstances())
  }, [dispatch])

  const searchOffers = useCallback((customFilters = {}) => {
    return dispatch(fetchOffers({ ...filters, ...customFilters }))
  }, [dispatch, filters])

  return {
    instances,
    offers,
    selectedOffer,
    stats,
    filters,
    loading,
    offersLoading,
    error,
    fetch,
    searchOffers,
  }
}

/**
 * Auto-fetch instances with polling
 */
export const useInstancesPolling = (intervalMs = 5000) => {
  const dispatch = useDispatch()
  const { instances, loading } = useSelector(state => state.instances)
  const { isAuthenticated } = useSelector(state => state.auth)

  useEffect(() => {
    if (!isAuthenticated) return

    // Initial fetch
    dispatch(fetchInstances())

    // Polling
    const interval = setInterval(() => {
      dispatch(fetchInstances())
    }, intervalMs)

    return () => clearInterval(interval)
  }, [dispatch, intervalMs, isAuthenticated])

  return { instances, loading }
}

/**
 * Initialize app - check auth and fetch user data
 */
export const useAppInit = () => {
  const dispatch = useDispatch()
  const { initialized, isAuthenticated } = useSelector(state => state.auth)
  const { hasCompletedOnboarding } = useSelector(state => state.user)

  useEffect(() => {
    if (!initialized) {
      dispatch(checkAuth()).then((action) => {
        if (action.type === 'auth/checkAuth/fulfilled') {
          dispatch(fetchUser())
        }
      })
    }
  }, [dispatch, initialized])

  return {
    initialized,
    isAuthenticated,
    hasCompletedOnboarding,
  }
}
