import { useState, useEffect } from 'react'
import { Server, Power, RefreshCw, Shield, Zap, DollarSign, Settings, AlertCircle } from 'lucide-react'

const API_BASE = ''

export default function StandbyConfig({ getAuthHeaders }) {
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [status, setStatus] = useState(null)
    const [error, setError] = useState(null)
    const [config, setConfig] = useState({
        enabled: false,
        gcp_zone: 'europe-west1-b',
        gcp_machine_type: 'e2-medium',
        gcp_disk_size: 100,
        gcp_spot: true,
        sync_interval: 30,
        auto_failover: true,
        auto_recovery: true,
    })
    const [pricing, setPricing] = useState(null)

    useEffect(() => {
        loadStatus()
        loadPricing()
    }, [])

    const loadStatus = async () => {
        try {
            const headers = getAuthHeaders ? getAuthHeaders() : {}
            const res = await fetch(`${API_BASE}/api/v1/standby/status`, {
                credentials: 'include',
                headers
            })
            if (res.ok) {
                const data = await res.json()
                setStatus(data)
                setConfig(prev => ({
                    ...prev,
                    enabled: data.auto_standby_enabled
                }))
            }
        } catch (err) {
            console.error('Error loading standby status:', err)
        } finally {
            setLoading(false)
        }
    }

    const loadPricing = async () => {
        try {
            const headers = getAuthHeaders ? getAuthHeaders() : {}
            const res = await fetch(`${API_BASE}/api/v1/standby/pricing?machine_type=${config.gcp_machine_type}&disk_gb=${config.gcp_disk_size}&spot=${config.gcp_spot}`, {
                credentials: 'include',
                headers
            })
            if (res.ok) {
                const data = await res.json()
                setPricing(data)
            }
        } catch (err) {
            console.error('Error loading pricing:', err)
        }
    }

    const saveConfig = async () => {
        setSaving(true)
        setError(null)
        try {
            const headers = getAuthHeaders ? getAuthHeaders() : {}
            const res = await fetch(`${API_BASE}/api/v1/standby/configure`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    ...headers,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(config)
            })

            if (res.ok) {
                await loadStatus()
            } else {
                const data = await res.json()
                setError(data.detail || 'Erro ao salvar configuração')
            }
        } catch (err) {
            setError(err.message)
        } finally {
            setSaving(false)
        }
    }

    useEffect(() => {
        loadPricing()
    }, [config.gcp_machine_type, config.gcp_disk_size, config.gcp_spot])

    if (loading) {
        return (
            <div className="standby-config loading">
                <div className="spinner" />
                <p>Carregando configuração...</p>
            </div>
        )
    }

    return (
        <div className="standby-config">
            <div className="config-header">
                <div className="header-title">
                    <Server size={22} />
                    <div>
                        <h3>CPU Standby / Failover</h3>
                        <p>Backup automático em VM CPU quando GPU falha</p>
                    </div>
                </div>
                <div className={`status-badge ${status?.auto_standby_enabled ? 'active' : 'inactive'}`}>
                    <Power size={14} />
                    {status?.auto_standby_enabled ? 'Ativo' : 'Inativo'}
                </div>
            </div>

            {error && (
                <div className="error-banner">
                    <AlertCircle size={16} />
                    {error}
                </div>
            )}

            <div className="config-grid">
                {/* Toggle Principal */}
                <div className="config-section full-width">
                    <label className="toggle-label">
                        <input
                            type="checkbox"
                            checked={config.enabled}
                            onChange={(e) => setConfig({ ...config, enabled: e.target.checked })}
                        />
                        <span className="toggle-slider"></span>
                        <span className="toggle-text">
                            Habilitar Auto-Standby
                            <small>Cria VM CPU automaticamente ao criar GPU</small>
                        </span>
                    </label>
                </div>

                {/* GCP Zone */}
                <div className="config-section">
                    <label>Zona GCP</label>
                    <select
                        value={config.gcp_zone}
                        onChange={(e) => setConfig({ ...config, gcp_zone: e.target.value })}
                        disabled={!config.enabled}
                    >
                        <option value="europe-west1-b">Europe West 1 (B)</option>
                        <option value="us-central1-a">US Central 1 (A)</option>
                        <option value="us-east1-b">US East 1 (B)</option>
                        <option value="asia-east1-a">Asia East 1 (A)</option>
                        <option value="southamerica-east1-a">South America East 1 (A)</option>
                    </select>
                </div>

                {/* Machine Type */}
                <div className="config-section">
                    <label>Tipo de Máquina</label>
                    <select
                        value={config.gcp_machine_type}
                        onChange={(e) => setConfig({ ...config, gcp_machine_type: e.target.value })}
                        disabled={!config.enabled}
                    >
                        <option value="e2-micro">e2-micro (2 vCPU, 1 GB)</option>
                        <option value="e2-small">e2-small (2 vCPU, 2 GB)</option>
                        <option value="e2-medium">e2-medium (2 vCPU, 4 GB)</option>
                        <option value="e2-standard-2">e2-standard-2 (2 vCPU, 8 GB)</option>
                        <option value="e2-standard-4">e2-standard-4 (4 vCPU, 16 GB)</option>
                    </select>
                </div>

                {/* Disk Size */}
                <div className="config-section">
                    <label>Disco (GB)</label>
                    <input
                        type="number"
                        value={config.gcp_disk_size}
                        onChange={(e) => setConfig({ ...config, gcp_disk_size: parseInt(e.target.value) })}
                        min={10}
                        max={500}
                        disabled={!config.enabled}
                    />
                </div>

                {/* Spot Toggle */}
                <div className="config-section">
                    <label className="toggle-label small">
                        <input
                            type="checkbox"
                            checked={config.gcp_spot}
                            onChange={(e) => setConfig({ ...config, gcp_spot: e.target.checked })}
                            disabled={!config.enabled}
                        />
                        <span className="toggle-slider"></span>
                        <span className="toggle-text">Usar Spot VM (70% mais barato)</span>
                    </label>
                </div>

                {/* Sync Interval */}
                <div className="config-section">
                    <label>Intervalo de Sync (segundos)</label>
                    <input
                        type="number"
                        value={config.sync_interval}
                        onChange={(e) => setConfig({ ...config, sync_interval: parseInt(e.target.value) })}
                        min={10}
                        max={300}
                        disabled={!config.enabled}
                    />
                </div>

                {/* Auto Failover */}
                <div className="config-section">
                    <label className="toggle-label small">
                        <input
                            type="checkbox"
                            checked={config.auto_failover}
                            onChange={(e) => setConfig({ ...config, auto_failover: e.target.checked })}
                            disabled={!config.enabled}
                        />
                        <span className="toggle-slider"></span>
                        <span className="toggle-text">Auto-Failover (troca para CPU se GPU falhar)</span>
                    </label>
                </div>

                {/* Auto Recovery */}
                <div className="config-section">
                    <label className="toggle-label small">
                        <input
                            type="checkbox"
                            checked={config.auto_recovery}
                            onChange={(e) => setConfig({ ...config, auto_recovery: e.target.checked })}
                            disabled={!config.enabled}
                        />
                        <span className="toggle-slider"></span>
                        <span className="toggle-text">Auto-Recovery (provisiona nova GPU após failover)</span>
                    </label>
                </div>
            </div>

            {/* Pricing Info */}
            {pricing && config.enabled && (
                <div className="pricing-info">
                    <DollarSign size={16} />
                    <span>
                        Custo estimado: <strong>${pricing.estimated_monthly_usd}/mês</strong>
                        {' '}({pricing.spot ? 'Spot' : 'On-Demand'})
                    </span>
                </div>
            )}

            {/* Current Associations */}
            {status && status.active_associations > 0 && (
                <div className="associations-info">
                    <Shield size={16} />
                    <span>
                        <strong>{status.active_associations}</strong> GPU(s) com backup ativo
                    </span>
                </div>
            )}

            {/* Save Button */}
            <div className="config-actions">
                <button
                    className="save-button"
                    onClick={saveConfig}
                    disabled={saving}
                >
                    {saving ? (
                        <>
                            <RefreshCw size={16} className="spin" />
                            Salvando...
                        </>
                    ) : (
                        <>
                            <Settings size={16} />
                            Salvar Configuração
                        </>
                    )}
                </button>
            </div>

            <style jsx>{`
        .standby-config {
          background: #161a16;
          border: 1px solid #30363d;
          border-radius: 12px;
          padding: 20px;
        }
        
        .config-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 20px;
        }
        
        .header-title {
          display: flex;
          gap: 12px;
          color: #3b82f6;
        }
        
        .header-title h3 {
          color: #fff;
          font-size: 16px;
          margin: 0;
        }
        
        .header-title p {
          color: #9ca3af;
          font-size: 12px;
          margin: 4px 0 0;
        }
        
        .status-badge {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          border-radius: 20px;
          font-size: 12px;
          font-weight: 500;
        }
        
        .status-badge.active {
          background: rgba(34, 197, 94, 0.2);
          color: #22c55e;
        }
        
        .status-badge.inactive {
          background: rgba(107, 114, 128, 0.2);
          color: #6b7280;
        }
        
        .error-banner {
          display: flex;
          align-items: center;
          gap: 8px;
          background: rgba(239, 68, 68, 0.2);
          color: #ef4444;
          padding: 12px;
          border-radius: 8px;
          margin-bottom: 16px;
          font-size: 13px;
        }
        
        .config-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 16px;
          margin-bottom: 20px;
        }
        
        .config-section {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        
        .config-section.full-width {
          grid-column: span 2;
        }
        
        .config-section label {
          color: #9ca3af;
          font-size: 12px;
        }
        
        .config-section input,
        .config-section select {
          background: #1c211c;
          border: 1px solid #30363d;
          color: #fff;
          padding: 10px;
          border-radius: 8px;
          font-size: 14px;
        }
        
        .config-section input:disabled,
        .config-section select:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        
        .toggle-label {
          display: flex;
          align-items: center;
          gap: 12px;
          cursor: pointer;
        }
        
        .toggle-label input {
          display: none;
        }
        
        .toggle-slider {
          width: 44px;
          height: 24px;
          background: #30363d;
          border-radius: 12px;
          position: relative;
          transition: background 0.2s;
        }
        
        .toggle-slider::after {
          content: '';
          position: absolute;
          width: 18px;
          height: 18px;
          background: #fff;
          border-radius: 50%;
          top: 3px;
          left: 3px;
          transition: transform 0.2s;
        }
        
        .toggle-label input:checked + .toggle-slider {
          background: #22c55e;
        }
        
        .toggle-label input:checked + .toggle-slider::after {
          transform: translateX(20px);
        }
        
        .toggle-text {
          display: flex;
          flex-direction: column;
          color: #fff;
          font-size: 14px;
        }
        
        .toggle-text small {
          color: #6b7280;
          font-size: 11px;
        }
        
        .toggle-label.small .toggle-text {
          font-size: 13px;
        }
        
        .pricing-info,
        .associations-info {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px;
          background: #1c211c;
          border-radius: 8px;
          margin-bottom: 12px;
          font-size: 13px;
          color: #9ca3af;
        }
        
        .pricing-info strong,
        .associations-info strong {
          color: #22c55e;
        }
        
        .config-actions {
          display: flex;
          justify-content: flex-end;
        }
        
        .save-button {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 20px;
          background: #22c55e;
          color: #000;
          border: none;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
          transition: background 0.2s;
        }
        
        .save-button:hover {
          background: #16a34a;
        }
        
        .save-button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        
        .spin {
          animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        
        .loading {
          text-align: center;
          padding: 40px;
          color: #9ca3af;
        }
        
        .spinner {
          width: 32px;
          height: 32px;
          border: 3px solid #30363d;
          border-top-color: #22c55e;
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin: 0 auto 12px;
        }
        
        @media (max-width: 600px) {
          .config-grid {
            grid-template-columns: 1fr;
          }
          .config-section.full-width {
            grid-column: span 1;
          }
        }
      `}</style>
        </div>
    )
}
