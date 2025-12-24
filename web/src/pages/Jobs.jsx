import React, { useState, useEffect, useCallback } from 'react';
import {
  Play, Square, RefreshCw, Clock, DollarSign, Cpu, Server,
  Plus, Loader2, CheckCircle, XCircle, AlertCircle, Terminal,
  Trash2, Eye, Download, ChevronDown, ChevronUp, ExternalLink
} from 'lucide-react';

// Status colors and icons
const STATUS_CONFIG = {
  pending: { color: 'text-gray-400', bg: 'bg-gray-500/10', icon: Clock, label: 'Pendente' },
  provisioning: { color: 'text-blue-400', bg: 'bg-blue-500/10', icon: Loader2, label: 'Provisionando' },
  starting: { color: 'text-blue-400', bg: 'bg-blue-500/10', icon: Loader2, label: 'Iniciando' },
  running: { color: 'text-emerald-400', bg: 'bg-emerald-500/10', icon: Play, label: 'Executando' },
  completing: { color: 'text-amber-400', bg: 'bg-amber-500/10', icon: Loader2, label: 'Finalizando' },
  completed: { color: 'text-emerald-400', bg: 'bg-emerald-500/10', icon: CheckCircle, label: 'Concluido' },
  failed: { color: 'text-red-400', bg: 'bg-red-500/10', icon: XCircle, label: 'Falhou' },
  cancelled: { color: 'text-gray-400', bg: 'bg-gray-500/10', icon: Square, label: 'Cancelado' },
  timeout: { color: 'text-amber-400', bg: 'bg-amber-500/10', icon: AlertCircle, label: 'Timeout' },
};

const Jobs = () => {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [creating, setCreating] = useState(false);
  const [expandedJob, setExpandedJob] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    source: 'huggingface',
    command: '',
    hf_repo: '',
    hf_revision: '',
    git_url: '',
    git_branch: '',
    setup_script: '',
    pip_packages: '',
    gpu_type: 'RTX 4090',
    disk_size: 50,
    timeout_minutes: 480,
  });

  // Fetch jobs
  const fetchJobs = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/jobs', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setJobs(data.jobs || []);
      }
    } catch (error) {
      console.error('Error fetching jobs:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
    // Auto-refresh every 10 seconds for running jobs
    const interval = setInterval(() => {
      if (jobs.some(j => ['pending', 'provisioning', 'starting', 'running', 'completing'].includes(j.status))) {
        fetchJobs();
      }
    }, 10000);
    return () => clearInterval(interval);
  }, [fetchJobs, jobs]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchJobs();
  };

  const handleCreateJob = async (e) => {
    e.preventDefault();
    setCreating(true);

    try {
      const payload = {
        name: formData.name,
        source: formData.source,
        command: formData.command,
        gpu_type: formData.gpu_type,
        disk_size: formData.disk_size,
        timeout_minutes: formData.timeout_minutes,
        pip_packages: formData.pip_packages ? formData.pip_packages.split(',').map(p => p.trim()) : [],
      };

      // Add source-specific fields
      if (formData.source === 'huggingface') {
        payload.hf_repo = formData.hf_repo;
        payload.hf_revision = formData.hf_revision || undefined;
      } else if (formData.source === 'git') {
        payload.git_url = formData.git_url;
        payload.git_branch = formData.git_branch || undefined;
      }

      if (formData.setup_script) {
        payload.setup_script = formData.setup_script;
      }

      const response = await fetch('/api/v1/jobs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        setShowCreateForm(false);
        setFormData({
          name: '',
          source: 'huggingface',
          command: '',
          hf_repo: '',
          hf_revision: '',
          git_url: '',
          git_branch: '',
          setup_script: '',
          pip_packages: '',
          gpu_type: 'RTX 4090',
          disk_size: 50,
          timeout_minutes: 480,
        });
        fetchJobs();
      } else {
        const error = await response.json();
        alert(`Erro ao criar job: ${error.detail || 'Erro desconhecido'}`);
      }
    } catch (error) {
      console.error('Error creating job:', error);
      alert('Erro ao criar job');
    } finally {
      setCreating(false);
    }
  };

  const handleCancelJob = async (jobId) => {
    if (!confirm('Tem certeza que deseja cancelar este job? A GPU sera destruida.')) {
      return;
    }

    try {
      const response = await fetch(`/api/v1/jobs/${jobId}/cancel`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (response.ok) {
        fetchJobs();
      }
    } catch (error) {
      console.error('Error cancelling job:', error);
    }
  };

  const JobStatusBadge = ({ status }) => {
    const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
    const Icon = config.icon;
    const isAnimated = ['provisioning', 'starting', 'running', 'completing'].includes(status);

    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.bg} ${config.color}`}>
        <Icon className={`w-3.5 h-3.5 ${isAnimated ? 'animate-spin' : ''}`} />
        {config.label}
      </span>
    );
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Jobs</h1>
          <p className="text-sm text-gray-400 mt-1">
            Execute tarefas em GPU e destrua automaticamente ao terminar
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-gray-200 transition-all border border-white/10"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => setShowCreateForm(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-500/20 hover:bg-brand-500/30 text-brand-400 border border-brand-500/30 transition-all"
          >
            <Plus className="w-4 h-4" />
            Novo Job
          </button>
        </div>
      </div>

      {/* Create Job Modal */}
      {showCreateForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-dark-surface-card border border-white/10 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-lg font-semibold text-gray-100">Novo Job</h2>
                  <p className="text-xs text-gray-500 mt-1">
                    Cria GPU, executa tarefa, destrói ao terminar
                  </p>
                </div>
                <button
                  onClick={() => setShowCreateForm(false)}
                  className="p-2 rounded-lg hover:bg-white/10 text-gray-400"
                >
                  <XCircle className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleCreateJob} className="space-y-5">
                {/* Nome */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">
                    Nome do Job *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="Ex: Fine-tune LLaMA"
                    className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 text-sm placeholder:text-gray-500 focus:ring-1 focus:ring-brand-500/50"
                  />
                </div>

                {/* Source Type */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">
                    Tipo de Fonte
                  </label>
                  <div className="flex gap-2">
                    {[
                      { id: 'huggingface', label: 'Hugging Face' },
                      { id: 'git', label: 'Git' },
                      { id: 'command', label: 'Comando' },
                    ].map((source) => (
                      <button
                        key={source.id}
                        type="button"
                        onClick={() => setFormData({ ...formData, source: source.id })}
                        className={`flex-1 px-3 py-2 rounded-lg border text-sm transition-all ${
                          formData.source === source.id
                            ? 'bg-brand-500/20 border-brand-500 text-brand-400'
                            : 'bg-white/5 border-white/10 text-gray-400 hover:bg-white/10'
                        }`}
                      >
                        {source.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Source-specific fields */}
                {formData.source === 'huggingface' && (
                  <div className="space-y-4 p-4 rounded-lg bg-white/5 border border-white/10">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-1.5">
                        Repositorio Hugging Face *
                      </label>
                      <input
                        type="text"
                        required
                        value={formData.hf_repo}
                        onChange={(e) => setFormData({ ...formData, hf_repo: e.target.value })}
                        placeholder="Ex: unsloth/llama-3-8b-Instruct-bnb-4bit"
                        className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 text-sm placeholder:text-gray-500 focus:ring-1 focus:ring-brand-500/50"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        O repositorio sera baixado para /workspace/model
                      </p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-1.5">
                        Revision (opcional)
                      </label>
                      <input
                        type="text"
                        value={formData.hf_revision}
                        onChange={(e) => setFormData({ ...formData, hf_revision: e.target.value })}
                        placeholder="main, v1.0, commit-hash..."
                        className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 text-sm placeholder:text-gray-500 focus:ring-1 focus:ring-brand-500/50"
                      />
                    </div>
                  </div>
                )}

                {formData.source === 'git' && (
                  <div className="space-y-4 p-4 rounded-lg bg-white/5 border border-white/10">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-1.5">
                        URL do Repositorio Git *
                      </label>
                      <input
                        type="text"
                        required
                        value={formData.git_url}
                        onChange={(e) => setFormData({ ...formData, git_url: e.target.value })}
                        placeholder="https://github.com/user/repo.git"
                        className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 text-sm placeholder:text-gray-500 focus:ring-1 focus:ring-brand-500/50"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-1.5">
                        Branch (opcional)
                      </label>
                      <input
                        type="text"
                        value={formData.git_branch}
                        onChange={(e) => setFormData({ ...formData, git_branch: e.target.value })}
                        placeholder="main"
                        className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 text-sm placeholder:text-gray-500 focus:ring-1 focus:ring-brand-500/50"
                      />
                    </div>
                  </div>
                )}

                {/* Command */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">
                    Comando a Executar {formData.source !== 'command' && '(opcional)'}
                  </label>
                  <textarea
                    value={formData.command}
                    onChange={(e) => setFormData({ ...formData, command: e.target.value })}
                    placeholder={formData.source === 'huggingface'
                      ? "python model/train.py --epochs 10"
                      : "python train.py --epochs 10"
                    }
                    rows={3}
                    className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 text-sm placeholder:text-gray-500 focus:ring-1 focus:ring-brand-500/50 font-mono"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Sera executado em /workspace. Crie /workspace/.job_complete quando terminar.
                  </p>
                </div>

                {/* GPU & Resources */}
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1.5">
                      GPU
                    </label>
                    <select
                      value={formData.gpu_type}
                      onChange={(e) => setFormData({ ...formData, gpu_type: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 text-sm focus:ring-1 focus:ring-brand-500/50"
                    >
                      <option value="RTX 3080">RTX 3080</option>
                      <option value="RTX 3090">RTX 3090</option>
                      <option value="RTX 4080">RTX 4080</option>
                      <option value="RTX 4090">RTX 4090</option>
                      <option value="A100">A100</option>
                      <option value="H100">H100</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1.5">
                      Disco (GB)
                    </label>
                    <input
                      type="number"
                      min="10"
                      max="500"
                      value={formData.disk_size}
                      onChange={(e) => setFormData({ ...formData, disk_size: parseInt(e.target.value) })}
                      className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 text-sm focus:ring-1 focus:ring-brand-500/50"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1.5">
                      Timeout (min)
                    </label>
                    <input
                      type="number"
                      min="10"
                      max="1440"
                      value={formData.timeout_minutes}
                      onChange={(e) => setFormData({ ...formData, timeout_minutes: parseInt(e.target.value) })}
                      className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 text-sm focus:ring-1 focus:ring-brand-500/50"
                    />
                  </div>
                </div>

                {/* Pip Packages */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">
                    Pip Packages (opcional)
                  </label>
                  <input
                    type="text"
                    value={formData.pip_packages}
                    onChange={(e) => setFormData({ ...formData, pip_packages: e.target.value })}
                    placeholder="transformers, accelerate, bitsandbytes"
                    className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 text-sm placeholder:text-gray-500 focus:ring-1 focus:ring-brand-500/50"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Separados por virgula. Serao instalados antes do comando.
                  </p>
                </div>

                {/* Actions */}
                <div className="flex justify-end gap-3 pt-4 border-t border-white/10">
                  <button
                    type="button"
                    onClick={() => setShowCreateForm(false)}
                    className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 text-sm transition-all"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={creating}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-500/20 hover:bg-brand-500/30 text-brand-400 border border-brand-500/30 text-sm transition-all disabled:opacity-50"
                  >
                    {creating ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Criando...
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4" />
                        Criar e Executar
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Jobs List */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400 mr-3" />
          <span className="text-gray-400">Carregando jobs...</span>
        </div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-20 border border-dashed border-white/10 rounded-xl">
          <Server className="w-12 h-12 mx-auto text-gray-600 mb-4" />
          <h3 className="text-lg font-medium text-gray-300 mb-2">Nenhum job criado</h3>
          <p className="text-sm text-gray-500 mb-6">
            Jobs executam tarefas em GPU e destroem automaticamente ao terminar
          </p>
          <button
            onClick={() => setShowCreateForm(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-500/20 hover:bg-brand-500/30 text-brand-400 border border-brand-500/30 transition-all"
          >
            <Plus className="w-4 h-4" />
            Criar Primeiro Job
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {jobs.map((job) => {
            const isExpanded = expandedJob === job.id;
            const isRunning = ['pending', 'provisioning', 'starting', 'running', 'completing'].includes(job.status);

            return (
              <div
                key={job.id}
                className="border border-white/10 rounded-xl bg-white/[0.02] overflow-hidden"
              >
                {/* Job Header */}
                <div
                  className="p-4 flex items-center gap-4 cursor-pointer hover:bg-white/[0.02] transition-all"
                  onClick={() => setExpandedJob(isExpanded ? null : job.id)}
                >
                  <div className="flex-shrink-0">
                    <Cpu className="w-5 h-5 text-gray-500" />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-200 truncate">
                        {job.name}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-gray-500">
                        {job.id}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                      <span>{job.gpu_type}</span>
                      <span>•</span>
                      <span>{job.source}</span>
                      {job.duration && (
                        <>
                          <span>•</span>
                          <Clock className="w-3 h-3" />
                          <span>{job.duration}</span>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    {job.total_cost > 0 && (
                      <div className="text-right">
                        <div className="text-xs text-gray-500">Custo</div>
                        <div className="text-sm font-mono text-gray-200">
                          ${job.total_cost.toFixed(4)}
                        </div>
                      </div>
                    )}

                    <JobStatusBadge status={job.status} />

                    {isRunning && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleCancelJob(job.id);
                        }}
                        className="p-1.5 rounded-lg hover:bg-red-500/10 text-red-400 transition-all"
                        title="Cancelar job"
                      >
                        <Square className="w-4 h-4" />
                      </button>
                    )}

                    <button className="p-1 text-gray-500">
                      {isExpanded ? (
                        <ChevronUp className="w-4 h-4" />
                      ) : (
                        <ChevronDown className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Job Details */}
                {isExpanded && (
                  <div className="px-4 pb-4 pt-2 border-t border-white/5 space-y-4">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <div className="text-xs text-gray-500 mb-1">Criado</div>
                        <div className="text-gray-300">
                          {new Date(job.created_at).toLocaleString('pt-BR')}
                        </div>
                      </div>
                      {job.started_at && (
                        <div>
                          <div className="text-xs text-gray-500 mb-1">Iniciado</div>
                          <div className="text-gray-300">
                            {new Date(job.started_at).toLocaleString('pt-BR')}
                          </div>
                        </div>
                      )}
                      {job.completed_at && (
                        <div>
                          <div className="text-xs text-gray-500 mb-1">Concluido</div>
                          <div className="text-gray-300">
                            {new Date(job.completed_at).toLocaleString('pt-BR')}
                          </div>
                        </div>
                      )}
                      {job.gpu_hours > 0 && (
                        <div>
                          <div className="text-xs text-gray-500 mb-1">GPU Hours</div>
                          <div className="text-gray-300">{job.gpu_hours.toFixed(4)}h</div>
                        </div>
                      )}
                    </div>

                    {job.ssh_host && job.ssh_port && (
                      <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                        <div className="text-xs text-gray-500 mb-1">SSH</div>
                        <code className="text-sm text-gray-300 font-mono">
                          ssh -p {job.ssh_port} root@{job.ssh_host}
                        </code>
                      </div>
                    )}

                    {job.error_message && (
                      <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                        <div className="text-xs text-red-400 mb-1">Erro</div>
                        <div className="text-sm text-red-300">{job.error_message}</div>
                      </div>
                    )}

                    <div className="flex items-center gap-2">
                      <a
                        href={`/api/v1/jobs/${job.id}/logs`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 text-xs transition-all"
                      >
                        <Terminal className="w-3.5 h-3.5" />
                        Ver Logs
                      </a>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Info Box */}
      <div className="p-4 rounded-xl bg-brand-500/5 border border-brand-500/20">
        <h4 className="text-sm font-medium text-brand-400 mb-2">Como funciona o modo Job?</h4>
        <ul className="text-xs text-gray-400 space-y-1">
          <li>• <strong>Cria</strong> uma GPU com a configuracao especificada</li>
          <li>• <strong>Baixa</strong> o repositorio do Hugging Face ou Git</li>
          <li>• <strong>Executa</strong> o comando especificado</li>
          <li>• <strong>Destrói</strong> a GPU automaticamente ao terminar (ou timeout)</li>
          <li>• Crie o arquivo <code className="bg-white/10 px-1 rounded">/workspace/.job_complete</code> para indicar conclusao</li>
        </ul>
      </div>
    </div>
  );
};

export default Jobs;
