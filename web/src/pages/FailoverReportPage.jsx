import React from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import FailoverReport from '../components/FailoverReport'

export default function FailoverReportPage() {
    const navigate = useNavigate()
    const location = useLocation()
    const basePath = location.pathname.startsWith('/demo-app') ? '/demo-app' : '/app'

    return (
        <div className="min-h-screen bg-[#0a0d0a] p-4 md:p-6 lg:p-8">
            {/* Header com botão de voltar */}
            <div className="max-w-7xl mx-auto mb-6">
                <button
                    onClick={() => navigate(`${basePath}/metrics-hub`)}
                    className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors mb-4"
                >
                    <ArrowLeft className="w-4 h-4" />
                    <span className="text-sm">Voltar para Métricas</span>
                </button>
            </div>

            {/* Conteúdo principal */}
            <div className="max-w-7xl mx-auto">
                <FailoverReport isDemo={localStorage.getItem('demo_mode') === 'true'} />
            </div>
        </div>
    )
}
