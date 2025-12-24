import React, { useState, useEffect, useRef } from 'react'
import {
    FiMessageSquare,
    FiSend,
    FiCpu,
    FiServer,
    FiRefreshCw,
    FiZap,
    FiTerminal
} from 'react-icons/fi'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'

export default function Chat() {
    const [models, setModels] = useState([])
    const [selectedModel, setSelectedModel] = useState(null)
    const [messages, setMessages] = useState([])
    const [inputText, setInputText] = useState('')
    const [loading, setLoading] = useState(false)
    const [connected, setConnected] = useState(false)
    const messagesEndRef = useRef(null)
    const [refreshing, setRefreshing] = useState(false)

    // Fetch available models
    const fetchModels = async () => {
        setRefreshing(true)
        try {
            const token = localStorage.getItem('auth_token')
            const res = await fetch('/api/chat/models', {
                headers: { Authorization: `Bearer ${token}` }
            })
            const data = await res.json()
            if (data.models) {
                setModels(data.models)
                // If current selected model is not in list anymore, deselect
                if (selectedModel && !data.models.find(m => m.id === selectedModel.id)) {
                    setSelectedModel(null)
                    setConnected(false)
                }
            }
        } catch (err) {
            console.error('Failed to fetch models:', err)
        } finally {
            setRefreshing(false)
        }
    }

    useEffect(() => {
        fetchModels()
        const interval = setInterval(fetchModels, 30000) // Poll every 30s
        return () => clearInterval(interval)
    }, [])

    // Auto-scroll to bottom of chat
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    const handleSelectModel = (model) => {
        setSelectedModel(model)
        setMessages([]) // Clear chat when switching
        setConnected(true) // Assume connected for now, could ping check
    }

    const handleSendMessage = async () => {
        if (!inputText.trim() || !selectedModel) return

        const userMsg = { role: 'user', content: inputText }
        setMessages(prev => [...prev, userMsg])
        setInputText('')
        setLoading(true)

        try {
            // Construct endpoint based on model type (assuming Ollama for now)
            // If we have a direct URL (ollama_url), use it.
            // Otherwise try to construct one.

            let baseUrl = selectedModel.ollama_url
            if (!baseUrl && selectedModel.ip) {
                // Default to port 11434 if not explicitly found but it's an "LLM" machine
                baseUrl = `http://${selectedModel.ip}:11434`
            }

            if (!baseUrl) {
                throw new Error("No URL available for this model")
            }

            const response = await fetch(`${baseUrl}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: 'llama3:latest', // Default or detect? Ollama needs a model name.
                    // Can default to 'llama2' or pull from list if we knew it.
                    // For the wizard, it installs 'ollama/ollama'. 
                    // We might need to 'pull' a model first if not present.
                    // Let's try 'llama3' or 'mistral' or just 'llama2' as a safe bet often pre-cached or small.
                    // Ideally, we should list models from the instance first: GET /api/tags
                    messages: [...messages, userMsg],
                    stream: false
                })
            })

            if (!response.ok) {
                // Fallback: maybe model usage is different or model name is wrong
                // Try to fetch tags to see what's installed
                try {
                    const tagsRes = await fetch(`${baseUrl}/api/tags`)
                    if (tagsRes.ok) {
                        const tagsData = await tagsRes.json()
                        if (tagsData.models && tagsData.models.length > 0) {
                            // Retry with the first available model
                            const firstModel = tagsData.models[0].name
                            const retryResponse = await fetch(`${baseUrl}/api/chat`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    model: firstModel,
                                    messages: [...messages, userMsg],
                                    stream: false
                                })
                            })
                            if (retryResponse.ok) {
                                const data = await retryResponse.json()
                                setMessages(prev => [...prev, { role: 'assistant', content: data.message.content }])
                                setLoading(false)
                                return
                            }
                        }
                    }
                } catch (e) {
                    console.error("Failed to recover model name", e)
                }

                throw new Error(`Chat request failed: ${response.statusText}`)
            }

            const data = await response.json()
            setMessages(prev => [...prev, { role: 'assistant', content: data.message.content }])

        } catch (error) {
            console.error('Send failed:', error)
            setMessages(prev => [...prev, { role: 'system', content: `Error: ${error.message}. Make sure the model is running and accessible.` }])
        } finally {
            setLoading(false)
        }
    }

    // Handle Enter key
    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSendMessage()
        }
    }

    return (
        <div className="flex h-[calc(100vh-6rem)] gap-6 p-6">
            {/* Sidebar - Model List */}
            <div className="w-80 flex-shrink-0 flex flex-col gap-4">
                <div className="flex items-center justify-between mb-2">
                    <h2 className="text-xl font-bold bg-gradient-to-r from-green-400 to-emerald-600 bg-clip-text text-transparent">
                        Available Models
                    </h2>
                    <button
                        onClick={fetchModels}
                        className={`p-2 rounded-full hover:bg-white/5 transition-all ${refreshing ? 'animate-spin' : ''}`}
                    >
                        <FiRefreshCw className="text-gray-400" />
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto space-y-3 pr-2 custom-scrollbar">
                    {models.length === 0 ? (
                        <div className="text-center py-10 text-gray-500 bg-white/5 rounded-xl border border-white/5 p-6 backdrop-blur-sm">
                            <FiServer className="w-8 h-8 mx-auto mb-3 opacity-50" />
                            <p>No active models found.</p>
                            <p className="text-sm mt-2 text-gray-400">Deploy a serverless instance to start.</p>
                        </div>
                    ) : (
                        models.map(model => (
                            <motion.div
                                key={model.id}
                                layoutId={`model-${model.id}`}
                                onClick={() => handleSelectModel(model)}
                                className={`
                  relative p-4 rounded-xl cursor-pointer border transition-all duration-200 group
                  ${selectedModel?.id === model.id
                                        ? 'bg-gradient-to-br from-green-500/10 to-emerald-500/5 border-green-500/50 shadow-[0_0_20px_rgba(16,185,129,0.1)]'
                                        : 'bg-[#161b22] border-white/5 hover:border-white/10 hover:bg-[#1c2128]'
                                    }
                `}
                            >
                                <div className="flex items-start justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className={`p-2 rounded-lg ${selectedModel?.id === model.id ? 'bg-green-500/20 text-green-400' : 'bg-white/5 text-gray-400 group-hover:text-gray-300'}`}>
                                            <FiCpu className="w-5 h-5" />
                                        </div>
                                        <div>
                                            <h3 className={`font-medium ${selectedModel?.id === model.id ? 'text-green-400' : 'text-gray-200'}`}>
                                                {model.gpu || 'Unknown GPU'}
                                            </h3>
                                            <p className="text-xs text-gray-500 mt-1 flex items-center gap-1">
                                                <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
                                                Running
                                            </p>
                                        </div>
                                    </div>
                                </div>
                                {model.ollama_url && (
                                    <div className="mt-3 text-xs font-mono text-gray-500 bg-black/20 p-1.5 rounded border border-white/5 flex items-center gap-2">
                                        <FiTerminal className="w-3 h-3" />
                                        Ollama Ready
                                    </div>
                                )}
                            </motion.div>
                        ))
                    )}
                </div>

                {/* Quick Deploy Button (Optional) */}
                <button className="flex items-center justify-center gap-2 p-3 bg-white/5 hover:bg-white/10 border border-white/5 rounded-xl transition-all text-sm font-medium text-gray-300 hover:text-white group">
                    <FiZap className="w-4 h-4 text-yellow-400 group-hover:scale-110 transition-transform" />
                    Deploy Serverless LLM
                </button>
            </div>

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col bg-[#161b22] border border-white/5 rounded-2xl overflow-hidden shadow-2xl relative">
                {!selectedModel ? (
                    <div className="flex-1 flex flex-col items-center justify-center text-gray-500 p-10 text-center">
                        <div className="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center mb-6 animate-float">
                            <FiMessageSquare className="w-8 h-8 text-gray-400" />
                        </div>
                        <h3 className="text-xl font-medium text-gray-300 mb-2">Select a Model</h3>
                        <p className="max-w-md text-gray-500">
                            Choose a running instance from the sidebar to verify availability and start chatting.
                        </p>
                    </div>
                ) : (
                    <>
                        {/* Chat Header */}
                        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 bg-[#0d1117]/50 backdrop-blur-md">
                            <div className="flex items-center gap-3">
                                <div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]"></div>
                                <div>
                                    <h3 className="font-medium text-gray-200">{selectedModel.name}</h3>
                                    <p className="text-xs text-gray-500 font-mono">{selectedModel.ip}</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="px-2 py-1 rounded text-xs bg-green-500/10 text-green-400 border border-green-500/20">
                                    Connected
                                </span>
                            </div>
                        </div>

                        {/* Messages */}
                        <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar bg-gradient-to-b from-[#0d1117] to-[#161b22]">
                            {messages.length === 0 && (
                                <div className="text-center py-20 text-gray-600">
                                    <p>Start a conversation with the model...</p>
                                </div>
                            )}
                            {messages.map((msg, idx) => (
                                <motion.div
                                    key={idx}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                                >
                                    <div
                                        className={`
                      max-w-[80%] rounded-2xl p-4 shadow-lg
                      ${msg.role === 'user'
                                                ? 'bg-green-600 text-white rounded-br-none'
                                                : 'bg-[#1c2128] border border-white/5 text-gray-200 rounded-bl-none'
                                            }
                    `}
                                    >
                                        <div className="prose prose-invert prose-sm">
                                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                                        </div>
                                    </div>
                                </motion.div>
                            ))}
                            {loading && (
                                <div className="flex justify-start">
                                    <div className="bg-[#1c2128] border border-white/5 rounded-2xl rounded-bl-none p-4 flex gap-1">
                                        <span className="w-2 h-2 rounded-full bg-gray-500 animate-bounce"></span>
                                        <span className="w-2 h-2 rounded-full bg-gray-500 animate-bounce delay-75"></span>
                                        <span className="w-2 h-2 rounded-full bg-gray-500 animate-bounce delay-150"></span>
                                    </div>
                                </div>
                            )}
                            <div ref={messagesEndRef} />
                        </div>

                        {/* Input Area */}
                        <div className="p-4 bg-[#161b22] border-t border-white/5">
                            <div className="relative">
                                <input
                                    type="text"
                                    value={inputText}
                                    onChange={(e) => setInputText(e.target.value)}
                                    onKeyDown={handleKeyDown}
                                    placeholder="Type your message..."
                                    disabled={loading}
                                    className="w-full bg-[#0d1117] border border-white/10 rounded-xl px-4 py-3 pr-12 text-gray-200 focus:outline-none focus:border-green-500/50 focus:ring-1 focus:ring-green-500/50 transition-all placeholder-gray-600"
                                />
                                <button
                                    onClick={handleSendMessage}
                                    disabled={loading || !inputText.trim()}
                                    className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-lg bg-green-600 text-white hover:bg-green-500 disabled:opacity-50 disabled:hover:bg-green-600 transition-all shadow-lg shadow-green-900/20"
                                >
                                    <FiSend className={`w-4 h-4 ${loading ? 'opacity-0' : ''}`} />
                                    {loading && <FiRefreshCw className="w-4 h-4 absolute top-2 left-2 animate-spin" />}
                                </button>
                            </div>
                            <p className="text-xs text-gray-500 mt-2 text-center">
                                Using local endpoint: {selectedModel.ollama_url || `http://${selectedModel.ip}:11434`}
                            </p>
                        </div>
                    </>
                )}
            </div>
        </div>
    )
}
