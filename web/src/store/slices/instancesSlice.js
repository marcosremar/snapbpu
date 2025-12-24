/**
 * Instances Slice - Manages GPU instances/machines state
 */
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'

const API_BASE = import.meta.env.VITE_API_URL || ''

const getToken = () => localStorage.getItem('auth_token')

// Async thunks
export const fetchInstances = createAsyncThunk(
  'instances/fetchInstances',
  async (_, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/instances`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch instances')
      }
      return data.instances || []
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const fetchOffers = createAsyncThunk(
  'instances/fetchOffers',
  async (filters = {}, { rejectWithValue }) => {
    try {
      const params = new URLSearchParams()
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== 'any' && value !== '' && value !== null && value !== undefined && value !== false && value !== 0) {
          params.append(key, value)
        }
      })
      const res = await fetch(`${API_BASE}/api/v1/instances/offers?${params}`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch offers')
      }
      return data.offers || []
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const createInstance = createAsyncThunk(
  'instances/createInstance',
  async (instanceConfig, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/instances`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getToken()}`,
        },
        body: JSON.stringify(instanceConfig),
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to create instance')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const startInstance = createAsyncThunk(
  'instances/startInstance',
  async (instanceId, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/instances/${instanceId}/start`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to start instance')
      }
      return { instanceId, ...data }
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const stopInstance = createAsyncThunk(
  'instances/stopInstance',
  async (instanceId, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/instances/${instanceId}/stop`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to stop instance')
      }
      return { instanceId, ...data }
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const destroyInstance = createAsyncThunk(
  'instances/destroyInstance',
  async (instanceId, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/instances/${instanceId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to destroy instance')
      }
      return instanceId
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

const initialState = {
  instances: [],
  offers: [],
  selectedOffer: null,
  stats: {
    activeMachines: 0,
    totalMachines: 0,
    dailyCost: 0,
    savings: 0,
    uptime: 0,
  },
  filters: {
    gpu_name: 'any',
    num_gpus: 1,
    min_gpu_ram: 0,
    min_cpu_cores: 1,
    min_cpu_ram: 1,
    min_disk: 50,
    max_price: 5.0,
    region: 'any',
    order_by: 'dph_total',
    limit: 100,
  },
  loading: false,
  offersLoading: false,
  error: null,
  lastFetch: null,
}

const instancesSlice = createSlice({
  name: 'instances',
  initialState,
  reducers: {
    setFilters: (state, action) => {
      state.filters = { ...state.filters, ...action.payload }
    },
    resetFilters: (state) => {
      state.filters = initialState.filters
    },
    setSelectedOffer: (state, action) => {
      state.selectedOffer = action.payload
    },
    clearSelectedOffer: (state) => {
      state.selectedOffer = null
    },
    updateInstanceStatus: (state, action) => {
      const { instanceId, status } = action.payload
      const instance = state.instances.find(i => i.id === instanceId)
      if (instance) {
        instance.status = status
      }
    },
    calculateStats: (state) => {
      const running = state.instances.filter(i => i.status === 'running')
      const totalCost = running.reduce((acc, i) => acc + (i.dph_total || 0), 0)
      state.stats = {
        activeMachines: running.length,
        totalMachines: state.instances.length,
        dailyCost: (totalCost * 24).toFixed(2),
        savings: ((totalCost * 24 * 0.89) * 30).toFixed(0),
        uptime: running.length > 0 ? 99.9 : 0,
      }
    },
    clearError: (state) => {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch Instances
      .addCase(fetchInstances.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchInstances.fulfilled, (state, action) => {
        state.loading = false
        state.instances = action.payload
        state.lastFetch = Date.now()
        // Recalculate stats
        const running = action.payload.filter(i => i.status === 'running')
        const totalCost = running.reduce((acc, i) => acc + (i.dph_total || 0), 0)
        state.stats = {
          activeMachines: running.length,
          totalMachines: action.payload.length,
          dailyCost: (totalCost * 24).toFixed(2),
          savings: ((totalCost * 24 * 0.89) * 30).toFixed(0),
          uptime: running.length > 0 ? 99.9 : 0,
        }
      })
      .addCase(fetchInstances.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Fetch Offers
      .addCase(fetchOffers.pending, (state) => {
        state.offersLoading = true
        state.error = null
      })
      .addCase(fetchOffers.fulfilled, (state, action) => {
        state.offersLoading = false
        state.offers = action.payload
      })
      .addCase(fetchOffers.rejected, (state, action) => {
        state.offersLoading = false
        state.error = action.payload
      })
      // Create Instance
      .addCase(createInstance.pending, (state) => {
        state.loading = true
      })
      .addCase(createInstance.fulfilled, (state, action) => {
        state.loading = false
        state.instances.push(action.payload)
      })
      .addCase(createInstance.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Start Instance
      .addCase(startInstance.fulfilled, (state, action) => {
        const instance = state.instances.find(i => i.id === action.payload.instanceId)
        if (instance) {
          instance.status = 'running'
        }
      })
      // Stop Instance
      .addCase(stopInstance.fulfilled, (state, action) => {
        const instance = state.instances.find(i => i.id === action.payload.instanceId)
        if (instance) {
          instance.status = 'stopped'
        }
      })
      // Destroy Instance
      .addCase(destroyInstance.fulfilled, (state, action) => {
        state.instances = state.instances.filter(i => i.id !== action.payload)
      })
  },
})

export const {
  setFilters,
  resetFilters,
  setSelectedOffer,
  clearSelectedOffer,
  updateInstanceStatus,
  calculateStats,
  clearError,
} = instancesSlice.actions

// Selectors
export const selectInstances = (state) => state.instances.instances
export const selectOffers = (state) => state.instances.offers
export const selectSelectedOffer = (state) => state.instances.selectedOffer
export const selectInstanceStats = (state) => state.instances.stats
export const selectInstanceFilters = (state) => state.instances.filters
export const selectInstancesLoading = (state) => state.instances.loading
export const selectOffersLoading = (state) => state.instances.offersLoading
export const selectInstancesError = (state) => state.instances.error
export const selectRunningInstances = (state) =>
  state.instances.instances.filter(i => i.status === 'running')

export default instancesSlice.reducer
