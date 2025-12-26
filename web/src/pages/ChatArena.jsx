import React, { useState, useEffect, useRef } from 'react'
import {
    FiMessageSquare,
    FiSend,
    FiCpu,
    FiServer,
    FiRefreshCw,
    FiZap,
    FiCheck,
    FiX,
    FiColumns,
    FiGrid,
    FiClock,
    FiChevronDown,
    FiSettings,
    FiDownload,
    FiInfo,
    FiEdit3,
    FiTrash2,
    FiActivity,
    FiFileText
} from 'react-icons/fi'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import { isDemoMode } from '../utils/api'

// Demo models for testing
const DEMO_MODELS = [
    { id: 'demo-1', gpu: 'RTX 4090 - Llama 3.1 70B', name: 'llama3.1:70b', ip: '192.168.1.100', ollama_url: null },
    { id: 'demo-2', gpu: 'RTX 3090 - Mistral 7B', name: 'mistral:7b', ip: '192.168.1.101', ollama_url: null },
    { id: 'demo-3', gpu: 'A100 - CodeLlama 34B', name: 'codellama:34b', ip: '192.168.1.102', ollama_url: null },
]

// Demo responses for simulation
const DEMO_RESPONSES = [
    "Olá! Sou um modelo de linguagem em modo demonstração. Posso ajudar com diversas tarefas como responder perguntas, gerar código, explicar conceitos e muito mais.",
    "Essa é uma excelente pergunta! Em modo demo, estou simulando respostas para demonstrar a funcionalidade do Chat Arena. Na versão real, você verá respostas dos modelos Ollama rodando nas suas GPUs.",
    "O Chat Arena permite comparar diferentes LLMs lado a lado. Você pode ver métricas como tokens/segundo, tempo de resposta e configurar system prompts diferentes para cada modelo.",
    "Aqui está um exemplo de código:\n```python\ndef hello_world():\n    print('Hello from Chat Arena!')\n    return 42\n```\nEste é apenas um exemplo demonstrativo.",
]

// Stats popover component
function StatsPopover({ stats, onClose }) {
    if (!stats) return null

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="absolute right-0 top-full mt-1 z-50 bg-[#1c2128] border border-white/10 rounded-lg shadow-xl p-3 min-w-[200px]"
            onClick={(e) => e.stopPropagation()}
        >
            <div className="text-xs space-y-2">
                <div className="flex justify-between">
                    <span className="text-gray-500">Tokens/s:</span>
                    <span className="text-purple-400 font-mono">{stats.tokensPerSecond?.toFixed(1) || '-'}</span>
                </div>
                <div className="flex justify-between">
                    <span className="text-gray-500">Total tokens:</span>
                    <span className="text-gray-300 font-mono">{stats.totalTokens || '-'}</span>
                </div>
                <div className="flex justify-between">
                    <span className="text-gray-500">Tempo resposta:</span>
                    <span className="text-gray-300 font-mono">{stats.responseTime ? `${(stats.responseTime / 1000).toFixed(2)}s` : '-'}</span>
                </div>
                <div className="flex justify-between">
                    <span className="text-gray-500">Time to first:</span>
                    <span className="text-gray-300 font-mono">{stats.timeToFirst ? `${stats.timeToFirst}ms` : '-'}</span>
                </div>
            </div>
        </motion.div>
    )
}

// System prompt editor modal
function SystemPromptModal({ isOpen, onClose, systemPrompt, onSave, modelName }) {
    const [prompt, setPrompt] = useState(systemPrompt)

    useEffect(() => {
        setPrompt(systemPrompt)
    }, [systemPrompt, isOpen])

    if (!isOpen) return null

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="relative bg-[#161b22] border border-white/10 rounded-xl shadow-2xl w-full max-w-lg mx-4 p-5"
            >
                <h3 className="text-lg font-medium text-gray-200 mb-1">System Prompt</h3>
                <p className="text-xs text-gray-500 mb-4">Customize o prompt de sistema para {modelName}</p>
                <textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="You are a helpful assistant..."
                    className="w-full h-40 bg-[#0d1117] border border-white/10 rounded-lg p-3 text-sm text-gray-200 focus:outline-none focus:border-purple-500/50 resize-none"
                />
                <div className="flex justify-end gap-2 mt-4">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-sm text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 rounded-lg transition-all"
                    >
                        Cancelar
                    </button>
                    <button
                        onClick={() => { onSave(prompt); onClose(); }}
                        className="px-4 py-2 text-sm text-white bg-purple-600 hover:bg-purple-500 rounded-lg transition-all"
                    >
                        Salvar
                    </button>
                </div>
            </motion.div>
        </div>
    )
}

export default function ChatArena() {
    const isDemo = isDemoMode()
    const [models, setModels] = useState([])
    const [selectedModels, setSelectedModels] = useState([])
    const [conversations, setConversations] = useState({}) // { modelId: { messages: [], loading: false, systemPrompt: '' } }
    const [modelConfigs, setModelConfigs] = useState({}) // { modelId: { systemPrompt: '' } }
    const [inputText, setInputText] = useState('')
    const [refreshing, setRefreshing] = useState(false)
    const [showModelSelector, setShowModelSelector] = useState(false)
    const [editingSystemPrompt, setEditingSystemPrompt] = useState(null) // modelId
    const [expandedStats, setExpandedStats] = useState(null) // messageId
    const [demoResponseIndex, setDemoResponseIndex] = useState(0)
    const messagesEndRef = useRef(null)
    const modelSelectorRef = useRef(null)

    // Fetch available models from API
    const fetchModels = async () => {
        setRefreshing(true)
        try {
            // Demo mode: use local demo data
            if (isDemo) {
                await new Promise(r => setTimeout(r, 300))
                setModels(DEMO_MODELS)
                setRefreshing(false)
                return
            }

            const token = localStorage.getItem('auth_token')
            const res = await fetch('/api/v1/chat/models', {
                headers: { Authorization: `Bearer ${token}` }
            })
            const data = await res.json()
            if (data.models) {
                setModels(data.models)
                setSelectedModels(prev => prev.filter(id => data.models.find(m => m.id === id)))
            }
        } catch (err) {
            console.error('Failed to fetch models:', err)
        } finally {
            setRefreshing(false)
        }
    }

    useEffect(() => {
        fetchModels()
        const interval = setInterval(fetchModels, 30000)
        return () => clearInterval(interval)
    }, [])

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [conversations])

    useEffect(() => {
        const handleClickOutside = (e) => {
            if (modelSelectorRef.current && !modelSelectorRef.current.contains(e.target)) {
                setShowModelSelector(false)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    const toggleModel = (modelId) => {
        setSelectedModels(prev => {
            if (prev.includes(modelId)) {
                return prev.filter(id => id !== modelId)
            }
            return [...prev, modelId]
        })
    }

    const getModelById = (id) => models.find(m => m.id === id)

    const getOllamaUrl = (model) => {
        if (model.ollama_url) return model.ollama_url
        if (model.ip) return `http://${model.ip}:11434`
        return null
    }

    // Estimate token count (rough approximation)
    const estimateTokens = (text) => {
        return Math.ceil(text.split(/\s+/).length * 1.3)
    }

    const sendMessageToModel = async (model, userMsg, messageHistory, systemPrompt) => {
        const startTime = Date.now()

        // Demo mode: simulate response
        if (isDemo) {
            const delay = 800 + Math.random() * 1500 // 0.8-2.3s delay
            await new Promise(r => setTimeout(r, delay))

            const responseTime = Date.now() - startTime
            const responseIdx = Math.floor(Math.random() * DEMO_RESPONSES.length)
            const content = DEMO_RESPONSES[responseIdx]
            const totalTokens = estimateTokens(content)
            const tokensPerSecond = totalTokens / (responseTime / 1000)

            return {
                content,
                stats: {
                    responseTime,
                    timeToFirst: Math.floor(delay * 0.3),
                    totalTokens,
                    tokensPerSecond,
                    modelUsed: model.name || 'demo-model'
                }
            }
        }

        const baseUrl = getOllamaUrl(model)
        if (!baseUrl) throw new Error("No URL available")

        let timeToFirst = null

        // Get model name from instance
        let modelName = 'llama3:latest'
        try {
            const tagsRes = await fetch(`${baseUrl}/api/tags`)
            if (tagsRes.ok) {
                const tagsData = await tagsRes.json()
                if (tagsData.models && tagsData.models.length > 0) {
                    modelName = tagsData.models[0].name
                }
            }
        } catch (e) { }

        // Build messages array with system prompt if provided
        const messages = []
        if (systemPrompt) {
            messages.push({ role: 'system', content: systemPrompt })
        }
        messages.push(...messageHistory, userMsg)

        const response = await fetch(`${baseUrl}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: modelName,
                messages,
                stream: false
            })
        })

        timeToFirst = Date.now() - startTime

        if (!response.ok) {
            throw new Error(`Request failed: ${response.statusText}`)
        }

        const data = await response.json()
        const responseTime = Date.now() - startTime
        const content = data.message?.content || 'No response'
        const totalTokens = estimateTokens(content)
        const tokensPerSecond = totalTokens / (responseTime / 1000)

        return {
            content,
            stats: {
                responseTime,
                timeToFirst,
                totalTokens,
                tokensPerSecond,
                modelUsed: modelName
            }
        }
    }

    const handleSendMessage = async () => {
        if (!inputText.trim() || selectedModels.length === 0) return

        const userMsg = { role: 'user', content: inputText, id: Date.now() }
        setInputText('')

        // Add user message to all selected conversations and set loading
        const updatedConversations = { ...conversations }
        selectedModels.forEach(modelId => {
            if (!updatedConversations[modelId]) {
                updatedConversations[modelId] = { messages: [], loading: false }
            }
            updatedConversations[modelId] = {
                ...updatedConversations[modelId],
                messages: [...updatedConversations[modelId].messages, userMsg],
                loading: true,
                startTime: Date.now()
            }
        })
        setConversations(updatedConversations)

        // Send to all models in parallel
        const promises = selectedModels.map(async (modelId) => {
            const model = getModelById(modelId)
            if (!model) return

            const messageHistory = conversations[modelId]?.messages?.filter(m => m.role !== 'system') || []
            const systemPrompt = modelConfigs[modelId]?.systemPrompt || ''

            try {
                const { content, stats } = await sendMessageToModel(model, userMsg, messageHistory, systemPrompt)

                setConversations(prev => ({
                    ...prev,
                    [modelId]: {
                        ...prev[modelId],
                        messages: [
                            ...prev[modelId].messages,
                            {
                                role: 'assistant',
                                content,
                                id: Date.now() + Math.random(),
                                stats
                            }
                        ],
                        loading: false
                    }
                }))
            } catch (error) {
                setConversations(prev => ({
                    ...prev,
                    [modelId]: {
                        ...prev[modelId],
                        messages: [
                            ...prev[modelId].messages,
                            {
                                role: 'system',
                                content: `Error: ${error.message}`,
                                isError: true,
                                id: Date.now() + Math.random()
                            }
                        ],
                        loading: false
                    }
                }))
            }
        })

        await Promise.allSettled(promises)
    }

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSendMessage()
        }
    }

    const clearConversations = () => {
        setConversations({})
    }

    const updateSystemPrompt = (modelId, prompt) => {
        setModelConfigs(prev => ({
            ...prev,
            [modelId]: { ...prev[modelId], systemPrompt: prompt }
        }))
    }

    const exportConversation = () => {
        const exportData = {
            timestamp: new Date().toISOString(),
            models: selectedModels.map(id => {
                const model = getModelById(id)
                const conv = conversations[id]
                return {
                    id,
                    name: model?.gpu || model?.name || 'Unknown',
                    ip: model?.ip,
                    systemPrompt: modelConfigs[id]?.systemPrompt || '',
                    messages: conv?.messages || [],
                    stats: conv?.messages?.filter(m => m.stats).map(m => ({
                        responseTime: m.stats.responseTime,
                        tokensPerSecond: m.stats.tokensPerSecond,
                        totalTokens: m.stats.totalTokens
                    }))
                }
            })
        }

        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `chat-arena-${new Date().toISOString().split('T')[0]}.json`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    }

    const exportAsMarkdown = () => {
        let md = `# Chat Arena - Comparativo de Modelos\n\n`
        md += `**Data:** ${new Date().toLocaleString()}\n\n---\n\n`

        selectedModels.forEach(modelId => {
            const model = getModelById(modelId)
            const conv = conversations[modelId]
            if (!conv) return

            md += `## ${model?.gpu || model?.name || 'Model'}\n`
            md += `**IP:** ${model?.ip || 'N/A'}\n\n`

            if (modelConfigs[modelId]?.systemPrompt) {
                md += `**System Prompt:** ${modelConfigs[modelId].systemPrompt}\n\n`
            }

            conv.messages.forEach(msg => {
                if (msg.role === 'user') {
                    md += `### User\n${msg.content}\n\n`
                } else if (msg.role === 'assistant') {
                    md += `### Assistant\n${msg.content}\n\n`
                    if (msg.stats) {
                        md += `> *${msg.stats.tokensPerSecond?.toFixed(1)} tokens/s | ${(msg.stats.responseTime / 1000).toFixed(2)}s | ${msg.stats.totalTokens} tokens*\n\n`
                    }
                }
            })

            md += `---\n\n`
        })

        const blob = new Blob([md], { type: 'text/markdown' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `chat-arena-${new Date().toISOString().split('T')[0]}.md`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    }

    const selectedModelObjects = selectedModels.map(id => getModelById(id)).filter(Boolean)
    const gridCols = selectedModels.length <= 2 ? selectedModels.length :
        selectedModels.length <= 4 ? 2 : 3

    return (
        <div className="flex flex-col h-[calc(100vh-6rem)] p-6 gap-4">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-gradient-to-br from-purple-500/20 to-pink-500/20 border border-purple-500/30">
                            <FiColumns className="w-5 h-5 text-purple-400" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-pink-500 bg-clip-text text-transparent">
                                Chat Arena
                            </h1>
                            <p className="text-sm text-gray-500">Compare LLMs lado a lado</p>
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    {/* Export Buttons */}
                    {selectedModels.length > 0 && Object.keys(conversations).length > 0 && (
                        <div className="flex items-center gap-2">
                            <button
                                onClick={exportAsMarkdown}
                                className="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 rounded-lg transition-all"
                                title="Exportar como Markdown"
                            >
                                <FiFileText className="w-4 h-4" />
                                <span className="hidden sm:inline">MD</span>
                            </button>
                            <button
                                onClick={exportConversation}
                                className="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 rounded-lg transition-all"
                                title="Exportar como JSON"
                            >
                                <FiDownload className="w-4 h-4" />
                                <span className="hidden sm:inline">JSON</span>
                            </button>
                        </div>
                    )}

                    {/* Model Selector Dropdown */}
                    <div className="relative" ref={modelSelectorRef}>
                        <button
                            onClick={() => setShowModelSelector(!showModelSelector)}
                            className="flex items-center gap-2 px-4 py-2 bg-[#161b22] border border-white/10 rounded-lg hover:border-purple-500/50 transition-all"
                        >
                            <FiCpu className="w-4 h-4 text-purple-400" />
                            <span className="text-gray-300">
                                {selectedModels.length === 0 ? 'Selecionar Modelos' : `${selectedModels.length} selecionado${selectedModels.length > 1 ? 's' : ''}`}
                            </span>
                            <FiChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${showModelSelector ? 'rotate-180' : ''}`} />
                        </button>

                        <AnimatePresence>
                            {showModelSelector && (
                                <motion.div
                                    initial={{ opacity: 0, y: -10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -10 }}
                                    className="absolute right-0 top-full mt-2 w-80 bg-[#161b22] border border-white/10 rounded-xl shadow-2xl z-50 overflow-hidden"
                                >
                                    <div className="p-3 border-b border-white/5 flex items-center justify-between">
                                        <span className="text-sm font-medium text-gray-300">Modelos Disponiveis</span>
                                        <button
                                            onClick={fetchModels}
                                            className={`p-1.5 rounded-lg hover:bg-white/5 transition-all ${refreshing ? 'animate-spin' : ''}`}
                                        >
                                            <FiRefreshCw className="w-4 h-4 text-gray-400" />
                                        </button>
                                    </div>
                                    <div className="max-h-64 overflow-y-auto p-2 space-y-1">
                                        {models.length === 0 ? (
                                            <div className="text-center py-6 text-gray-500">
                                                <FiServer className="w-6 h-6 mx-auto mb-2 opacity-50" />
                                                <p className="text-sm">Nenhum modelo disponivel</p>
                                            </div>
                                        ) : (
                                            models.map(model => (
                                                <button
                                                    key={model.id}
                                                    onClick={() => toggleModel(model.id)}
                                                    className={`w-full flex items-center gap-3 p-3 rounded-lg transition-all ${selectedModels.includes(model.id)
                                                        ? 'bg-purple-500/10 border border-purple-500/30'
                                                        : 'hover:bg-white/5 border border-transparent'
                                                        }`}
                                                >
                                                    <div className={`w-5 h-5 rounded flex items-center justify-center ${selectedModels.includes(model.id)
                                                        ? 'bg-purple-500 text-white'
                                                        : 'bg-white/10'
                                                        }`}>
                                                        {selectedModels.includes(model.id) && <FiCheck className="w-3 h-3" />}
                                                    </div>
                                                    <div className="flex-1 text-left">
                                                        <p className="text-sm font-medium text-gray-200">{model.gpu || model.name || 'Unknown'}</p>
                                                        <p className="text-xs text-gray-500">{model.ip}</p>
                                                    </div>
                                                    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                                                </button>
                                            ))
                                        )}
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>

                    {selectedModels.length > 0 && (
                        <button
                            onClick={clearConversations}
                            className="p-2 text-gray-400 hover:text-red-400 bg-white/5 hover:bg-red-500/10 rounded-lg transition-all"
                            title="Limpar conversas"
                        >
                            <FiTrash2 className="w-4 h-4" />
                        </button>
                    )}
                </div>
            </div>

            {/* Main Chat Area */}
            {selectedModels.length === 0 ? (
                <div className="flex-1 flex items-center justify-center">
                    <div className="text-center max-w-md">
                        <div className="w-20 h-20 bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-full flex items-center justify-center mx-auto mb-6 border border-purple-500/20">
                            <FiGrid className="w-8 h-8 text-purple-400/60" />
                        </div>
                        <h3 className="text-xl font-medium text-gray-300 mb-2">Selecione Modelos para Comparar</h3>
                        <p className="text-gray-500 mb-6">
                            Escolha 2 ou mais modelos do dropdown acima para comparar suas respostas lado a lado.
                        </p>
                        <button
                            onClick={() => setShowModelSelector(true)}
                            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg text-white font-medium hover:from-purple-500 hover:to-pink-500 transition-all shadow-lg shadow-purple-900/30"
                        >
                            <FiCpu className="w-4 h-4" />
                            Selecionar Modelos
                        </button>
                    </div>
                </div>
            ) : (
                <>
                    {/* Response Grid */}
                    <div
                        className="flex-1 grid gap-4 overflow-hidden"
                        style={{ gridTemplateColumns: `repeat(${gridCols}, 1fr)` }}
                    >
                        {selectedModelObjects.map(model => {
                            const conv = conversations[model.id] || { messages: [], loading: false }
                            const systemPrompt = modelConfigs[model.id]?.systemPrompt || ''

                            return (
                                <div
                                    key={model.id}
                                    className="flex flex-col bg-[#161b22] border border-white/5 rounded-xl overflow-hidden"
                                >
                                    {/* Model Header */}
                                    <div className="flex items-center justify-between px-4 py-3 border-b border-white/5 bg-[#0d1117]/50">
                                        <div className="flex items-center gap-2">
                                            <div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]" />
                                            <span className="text-sm font-medium text-gray-200">{model.gpu || model.name || 'Model'}</span>
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <button
                                                onClick={() => setEditingSystemPrompt(model.id)}
                                                className={`p-1.5 rounded hover:bg-white/10 transition-all ${systemPrompt ? 'text-purple-400' : 'text-gray-500 hover:text-gray-300'}`}
                                                title="System Prompt"
                                            >
                                                <FiSettings className="w-4 h-4" />
                                            </button>
                                            <button
                                                onClick={() => toggleModel(model.id)}
                                                className="p-1.5 rounded hover:bg-white/10 transition-all"
                                            >
                                                <FiX className="w-4 h-4 text-gray-500 hover:text-red-400" />
                                            </button>
                                        </div>
                                    </div>

                                    {/* System Prompt Indicator */}
                                    {systemPrompt && (
                                        <div className="px-4 py-2 bg-purple-500/5 border-b border-purple-500/10">
                                            <p className="text-xs text-purple-400 truncate">
                                                <FiEdit3 className="w-3 h-3 inline mr-1" />
                                                {systemPrompt.slice(0, 50)}{systemPrompt.length > 50 ? '...' : ''}
                                            </p>
                                        </div>
                                    )}

                                    {/* Messages */}
                                    <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
                                        {conv.messages.length === 0 && !conv.loading && (
                                            <div className="text-center py-10 text-gray-600 text-sm">
                                                Aguardando mensagem...
                                            </div>
                                        )}
                                        {conv.messages.map((msg, idx) => (
                                            <motion.div
                                                key={msg.id || idx}
                                                initial={{ opacity: 0, y: 5 }}
                                                animate={{ opacity: 1, y: 0 }}
                                                className={`${msg.role === 'user' ? 'ml-4' : 'mr-4'}`}
                                            >
                                                <div
                                                    className={`rounded-xl p-3 text-sm ${msg.role === 'user'
                                                        ? 'bg-purple-600 text-white ml-auto max-w-[90%]'
                                                        : msg.isError
                                                            ? 'bg-red-500/10 border border-red-500/30 text-red-300'
                                                            : 'bg-[#1c2128] border border-white/5 text-gray-200'
                                                        }`}
                                                >
                                                    <div className="prose prose-invert prose-sm max-w-none">
                                                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                                                    </div>

                                                    {/* Stats for assistant messages */}
                                                    {msg.stats && (
                                                        <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/10 text-xs text-gray-500">
                                                            <div className="flex items-center gap-3">
                                                                <span className="flex items-center gap-1">
                                                                    <FiActivity className="w-3 h-3" />
                                                                    {msg.stats.tokensPerSecond?.toFixed(1)} t/s
                                                                </span>
                                                                <span className="flex items-center gap-1">
                                                                    <FiClock className="w-3 h-3" />
                                                                    {(msg.stats.responseTime / 1000).toFixed(2)}s
                                                                </span>
                                                            </div>
                                                            <div className="relative">
                                                                <button
                                                                    onClick={() => setExpandedStats(expandedStats === msg.id ? null : msg.id)}
                                                                    className="p-1 rounded hover:bg-white/10 transition-all"
                                                                    title="Ver detalhes"
                                                                >
                                                                    <FiInfo className="w-3 h-3" />
                                                                </button>
                                                                <AnimatePresence>
                                                                    {expandedStats === msg.id && (
                                                                        <StatsPopover
                                                                            stats={msg.stats}
                                                                            onClose={() => setExpandedStats(null)}
                                                                        />
                                                                    )}
                                                                </AnimatePresence>
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                            </motion.div>
                                        ))}
                                        {conv.loading && (
                                            <div className="flex items-center gap-2 text-gray-500">
                                                <div className="flex gap-1">
                                                    <span className="w-2 h-2 rounded-full bg-purple-500 animate-bounce" />
                                                    <span className="w-2 h-2 rounded-full bg-purple-500 animate-bounce delay-75" />
                                                    <span className="w-2 h-2 rounded-full bg-purple-500 animate-bounce delay-150" />
                                                </div>
                                                <span className="text-xs">Pensando...</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )
                        })}
                    </div>

                    {/* Input Area */}
                    <div className="bg-[#161b22] border border-white/5 rounded-xl p-4">
                        <div className="relative">
                            <input
                                type="text"
                                value={inputText}
                                onChange={(e) => setInputText(e.target.value)}
                                onKeyDown={handleKeyDown}
                                placeholder={`Enviar mensagem para ${selectedModels.length} modelo${selectedModels.length > 1 ? 's' : ''}...`}
                                disabled={Object.values(conversations).some(c => c.loading)}
                                className="w-full bg-[#0d1117] border border-white/10 rounded-xl px-4 py-3 pr-12 text-gray-200 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50 transition-all placeholder-gray-600"
                            />
                            <button
                                onClick={handleSendMessage}
                                disabled={Object.values(conversations).some(c => c.loading) || !inputText.trim()}
                                className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-lg bg-gradient-to-r from-purple-600 to-pink-600 text-white hover:from-purple-500 hover:to-pink-500 disabled:opacity-50 disabled:hover:from-purple-600 disabled:hover:to-pink-600 transition-all shadow-lg shadow-purple-900/20"
                            >
                                <FiSend className="w-4 h-4" />
                            </button>
                        </div>
                        <p className="text-xs text-gray-500 mt-2 text-center">
                            Enter para enviar - Mensagens enviadas para todos os modelos simultaneamente
                        </p>
                    </div>
                </>
            )}

            {/* System Prompt Modal */}
            <AnimatePresence>
                {editingSystemPrompt && (
                    <SystemPromptModal
                        isOpen={!!editingSystemPrompt}
                        onClose={() => setEditingSystemPrompt(null)}
                        systemPrompt={modelConfigs[editingSystemPrompt]?.systemPrompt || ''}
                        onSave={(prompt) => updateSystemPrompt(editingSystemPrompt, prompt)}
                        modelName={getModelById(editingSystemPrompt)?.gpu || getModelById(editingSystemPrompt)?.name || 'Model'}
                    />
                )}
            </AnimatePresence>

            <div ref={messagesEndRef} />
        </div>
    )
}
