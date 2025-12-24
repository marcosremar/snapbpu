/**
 * Redux Store Configuration
 * Central state management for DumontCloud
 */
import { configureStore } from '@reduxjs/toolkit'
import authSlice from './slices/authSlice'
import userSlice from './slices/userSlice'
import instancesSlice from './slices/instancesSlice'
import uiSlice from './slices/uiSlice'

export const store = configureStore({
  reducer: {
    auth: authSlice,
    user: userSlice,
    instances: instancesSlice,
    ui: uiSlice,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore these action types for serialization check
        ignoredActions: ['instances/setSelectedOffer'],
      },
    }),
  devTools: import.meta.env.DEV,
})

// Infer the `RootState` and `AppDispatch` types from the store itself
export const RootState = store.getState
export const AppDispatch = store.dispatch

export default store
