import { useState, useEffect } from 'react';
import {
  Brain,
  Plus,
  RefreshCw,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  Play,
  Square,
  FileText,
  Trash2,
  ChevronDown,
  AlertCircle,
  Cpu,
  Database,
  Rocket,
  Download,
  Server,
} from 'lucide-react';
import { Button, Progress } from '../components/tailadmin-ui';
import FineTuningModal from '../components/FineTuningModal';

// Status configurations
const STATUS_CONFIG = {
  pending: { icon: Clock, color: 'text-yellow-400', bg: 'bg-yellow-400/10', label: 'Pending' },
  uploading: { icon: Loader2, color: 'text-cyan-400', bg: 'bg-cyan-400/10', label: 'Uploading', spin: true },
  queued: { icon: Clock, color: 'text-orange-400', bg: 'bg-orange-400/10', label: 'Queued' },
  running: { icon: Loader2, color: 'text-purple-400', bg: 'bg-purple-400/10', label: 'Running', spin: true },
  completed: { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-400/10', label: 'Completed' },
  failed: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-400/10', label: 'Failed' },
  cancelled: { icon: Square, color: 'text-gray-400', bg: 'bg-gray-400/10', label: 'Cancelled' },
};

// Format relative time
function formatTimeAgo(dateStr) {
  if (!dateStr) return 'N/A';
  const date = new Date(dateStr);
  const now = new Date();
  const seconds = Math.floor((now - date) / 1000);

  if (seconds < 60) return 'Just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

// Job Card Component
function JobCard({ job, onRefresh, onViewLogs, onCancel, onDeploy, onDownload }) {
  const status = STATUS_CONFIG[job.status] || STATUS_CONFIG.pending;
  const StatusIcon = status.icon;
  const isRunning = job.status === 'running' || job.status === 'queued';
  const isCompleted = job.status === 'completed';

  return (
    <div className="bg-[#131713] rounded-xl border border-white/10 p-5 hover:border-white/20 transition-all shadow-sm">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${status.bg}`}>
            <StatusIcon className={`w-5 h-5 ${status.color} ${status.spin ? 'animate-spin' : ''}`} />
          </div>
          <div>
            <h3 className="font-semibold text-white">{job.name}</h3>
            <p className="text-sm text-gray-400">{job.id}</p>
          </div>
        </div>
        <span className={`text-xs px-2 py-1 rounded ${status.bg} ${status.color}`}>
          {status.label}
        </span>
      </div>

      {/* Model & Dataset */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="flex items-center gap-2 text-sm">
          <Cpu className="w-4 h-4 text-gray-400" />
          <span className="text-gray-400">Model:</span>
          <span className="text-white truncate">{job.base_model.split('/').pop()}</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <Database className="w-4 h-4 text-gray-400" />
          <span className="text-gray-400">GPU:</span>
          <span className="text-white">{job.gpu_type}</span>
        </div>
      </div>

      {/* Progress (for running jobs) */}
      {isRunning && (
        <div className="mb-4">
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-400">
              Epoch {job.current_epoch + 1} / {job.config?.epochs || 1}
            </span>
            <span className="text-purple-400">{job.progress_percent?.toFixed(1) || 0}%</span>
          </div>
          <Progress value={job.progress_percent || 0} className="h-2" />
          {job.loss && (
            <div className="text-xs text-gray-400 mt-1">
              Loss: {job.loss.toFixed(4)}
            </div>
          )}
        </div>
      )}

      {/* Error message */}
      {job.status === 'failed' && job.error_message && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
            <p className="text-sm text-red-400 line-clamp-2">{job.error_message}</p>
          </div>
        </div>
      )}

      {/* Timestamps */}
      <div className="flex items-center justify-between text-xs text-gray-400 mb-4">
        <span>Created {formatTimeAgo(job.created_at)}</span>
        {job.completed_at && <span>Completed {formatTimeAgo(job.completed_at)}</span>}
      </div>

      {/* Actions */}
      <div className="flex flex-wrap gap-2 pt-3 border-t border-white/10">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onViewLogs(job)}
          className="text-gray-400 hover:text-white"
        >
          <FileText className="w-4 h-4 mr-1" />
          Logs
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onRefresh(job.id)}
          className="text-gray-400 hover:text-white"
        >
          <RefreshCw className="w-4 h-4 mr-1" />
          Refresh
        </Button>
        {isCompleted && (
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDeploy(job)}
              className="text-green-400 hover:text-green-300"
            >
              <Rocket className="w-4 h-4 mr-1" />
              Deploy
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDownload(job)}
              className="text-cyan-400 hover:text-cyan-300"
            >
              <Download className="w-4 h-4 mr-1" />
              Download
            </Button>
          </>
        )}
        {isRunning && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onCancel(job.id)}
            className="text-red-400 hover:text-red-300 ml-auto"
          >
            <Square className="w-4 h-4 mr-1" />
            Cancel
          </Button>
        )}
      </div>
    </div>
  );
}

// Logs Modal Component
function LogsModal({ job, isOpen, onClose }) {
  const [logs, setLogs] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isOpen && job) {
      fetchLogs();
    }
  }, [isOpen, job]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`/api/finetune/jobs/${job.id}/logs?tail=200`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
      const data = await res.json();
      setLogs(data.logs || 'No logs available');
    } catch (err) {
      setLogs('Failed to fetch logs: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-[#1a1f2e] rounded-xl border border-gray-700 w-full max-w-4xl max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h3 className="text-lg font-semibold text-white">Logs: {job.name}</h3>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={fetchLogs}>
              <RefreshCw className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
        <div className="flex-1 overflow-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center h-40">
              <Loader2 className="w-6 h-6 text-purple-400 animate-spin" />
            </div>
          ) : (
            <pre className="text-sm text-gray-300 font-mono whitespace-pre-wrap">
              {logs}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}

// Deploy Modal Component
function DeployModal({ job, isOpen, onClose, onSuccess }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedGpu, setSelectedGpu] = useState('RTX4090');
  const [instanceName, setInstanceName] = useState('');

  useEffect(() => {
    if (job) {
      setInstanceName(`inference-${job.name.slice(0, 20)}`);
    }
  }, [job]);

  const GPU_OPTIONS = [
    { id: 'RTX4090', name: 'RTX 4090', vram: '24GB', price: '~$0.35/hr' },
    { id: 'A100', name: 'A100 40GB', vram: '40GB', price: '~$1.50/hr' },
    { id: 'A100-80GB', name: 'A100 80GB', vram: '80GB', price: '~$2.00/hr' },
    { id: 'H100', name: 'H100 80GB', vram: '80GB', price: '~$3.50/hr' },
  ];

  const handleDeploy = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`/api/finetune/jobs/${job.id}/deploy`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          gpu_type: selectedGpu,
          instance_name: instanceName,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Failed to deploy model');
      }
      onSuccess(data);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-[#1a1f2e] rounded-xl border border-gray-700 w-full max-w-lg">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <Rocket className="w-5 h-5 text-green-400" />
            Deploy Model
          </h3>
          <Button variant="ghost" size="sm" onClick={onClose}>
            ✕
          </Button>
        </div>

        <div className="p-6 space-y-6">
          {/* Model Info */}
          <div className="bg-[#0f1219] rounded-lg p-4 border border-gray-700/50">
            <div className="flex items-center gap-3 mb-2">
              <Brain className="w-5 h-5 text-purple-400" />
              <span className="text-white font-medium">{job?.name}</span>
            </div>
            <div className="text-sm text-gray-400">
              Base: {job?.config?.base_model?.split('/').pop() || 'Unknown'}
            </div>
            <div className="text-sm text-gray-400">
              LoRA Rank: {job?.config?.lora_rank || 16}
            </div>
          </div>

          {/* Instance Name */}
          <div>
            <label className="block text-sm text-gray-400 mb-2">Instance Name</label>
            <input
              type="text"
              value={instanceName}
              onChange={(e) => setInstanceName(e.target.value)}
              className="w-full bg-[#0f1219] border border-gray-700 rounded-lg px-4 py-2 text-white focus:border-purple-500 outline-none"
              placeholder="my-inference-instance"
            />
          </div>

          {/* GPU Selection */}
          <div>
            <label className="block text-sm text-gray-400 mb-2">Select GPU</label>
            <div className="grid grid-cols-2 gap-3">
              {GPU_OPTIONS.map((gpu) => (
                <button
                  key={gpu.id}
                  onClick={() => setSelectedGpu(gpu.id)}
                  className={`p-3 rounded-lg border transition-all text-left ${
                    selectedGpu === gpu.id
                      ? 'border-green-500 bg-green-500/10'
                      : 'border-gray-700 hover:border-gray-600'
                  }`}
                >
                  <div className="font-medium text-white">{gpu.name}</div>
                  <div className="text-xs text-gray-400">{gpu.vram} • {gpu.price}</div>
                </button>
              ))}
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <Button variant="ghost" onClick={onClose} className="flex-1">
              Cancel
            </Button>
            <Button
              onClick={handleDeploy}
              disabled={loading || !instanceName}
              className="flex-1 bg-green-500 hover:bg-green-600 text-white"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <Server className="w-4 h-4 mr-2" />
              )}
              Deploy Instance
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Main Page Component
export default function FineTuning() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [selectedJob, setSelectedJob] = useState(null);
  const [showLogs, setShowLogs] = useState(false);
  const [showDeploy, setShowDeploy] = useState(false);
  const [filter, setFilter] = useState('all');

  // Fetch jobs
  const fetchJobs = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch('/api/finetune/jobs', {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
      const data = await res.json();
      setJobs(data.jobs || []);
    } catch (err) {
      console.error('Failed to fetch jobs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    // Poll for updates every 10 seconds
    const interval = setInterval(fetchJobs, 10000);
    return () => clearInterval(interval);
  }, []);

  // Refresh single job
  const handleRefresh = async (jobId) => {
    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`/api/finetune/jobs/${jobId}/refresh`, {
        method: 'POST',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
      const updatedJob = await res.json();
      setJobs(jobs.map(j => j.id === jobId ? updatedJob : j));
    } catch (err) {
      console.error('Failed to refresh job:', err);
    }
  };

  // Cancel job
  const handleCancel = async (jobId) => {
    if (!confirm('Are you sure you want to cancel this job?')) return;
    try {
      const token = localStorage.getItem('auth_token');
      await fetch(`/api/finetune/jobs/${jobId}/cancel`, {
        method: 'POST',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
      fetchJobs();
    } catch (err) {
      console.error('Failed to cancel job:', err);
    }
  };

  // View logs
  const handleViewLogs = (job) => {
    setSelectedJob(job);
    setShowLogs(true);
  };

  // Deploy model
  const handleDeploy = (job) => {
    setSelectedJob(job);
    setShowDeploy(true);
  };

  // Download model
  const handleDownload = async (job) => {
    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`/api/finetune/jobs/${job.id}/download`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
      const data = await res.json();
      if (data.download_url) {
        window.open(data.download_url, '_blank');
      } else if (data.message) {
        alert(data.message);
      }
    } catch (err) {
      alert('Failed to download: ' + err.message);
    }
  };

  // Filter jobs
  const filteredJobs = jobs.filter(job => {
    if (filter === 'all') return true;
    if (filter === 'running') return ['pending', 'uploading', 'queued', 'running'].includes(job.status);
    if (filter === 'completed') return job.status === 'completed';
    if (filter === 'failed') return job.status === 'failed';
    return true;
  });

  // Stats
  const stats = {
    total: jobs.length,
    running: jobs.filter(j => ['running', 'queued', 'pending'].includes(j.status)).length,
    completed: jobs.filter(j => j.status === 'completed').length,
    failed: jobs.filter(j => j.status === 'failed').length,
  };

  return (
    <div className="min-h-screen bg-[#0a0d0a] p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Brain className="w-7 h-7 text-purple-400" />
            Fine-Tuning
          </h1>
          <p className="text-gray-400 mt-1">Train custom models with Unsloth</p>
        </div>
        <Button
          onClick={() => setShowModal(true)}
          className="bg-purple-500 hover:bg-purple-600 text-white gap-2"
        >
          <Plus className="w-4 h-4" />
          New Fine-Tune Job
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-[#111411] rounded-xl p-4 border border-white/10 shadow-sm">
          <div className="text-3xl font-bold text-white">{stats.total}</div>
          <div className="text-sm text-gray-400">Total Jobs</div>
        </div>
        <div className="bg-[#111411] rounded-xl p-4 border border-white/10 shadow-sm">
          <div className="text-3xl font-bold text-purple-400">{stats.running}</div>
          <div className="text-sm text-gray-400">Running</div>
        </div>
        <div className="bg-[#111411] rounded-xl p-4 border border-white/10 shadow-sm">
          <div className="text-3xl font-bold text-green-400">{stats.completed}</div>
          <div className="text-sm text-gray-400">Completed</div>
        </div>
        <div className="bg-[#111411] rounded-xl p-4 border border-white/10 shadow-sm">
          <div className="text-3xl font-bold text-red-400">{stats.failed}</div>
          <div className="text-sm text-gray-400">Failed</div>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 mb-6">
        {['all', 'running', 'completed', 'failed'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              filter === f
                ? 'bg-purple-500 text-white'
                : 'bg-white/5 text-gray-400 hover:text-white hover:bg-white/10'
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
        <Button
          variant="ghost"
          size="sm"
          onClick={fetchJobs}
          className="ml-auto text-gray-400 hover:text-white"
        >
          <RefreshCw className="w-4 h-4 mr-1" />
          Refresh
        </Button>
      </div>

      {/* Jobs Grid */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
        </div>
      ) : filteredJobs.length === 0 ? (
        <div className="text-center py-16 bg-[#111411] rounded-xl border border-white/10 shadow-sm">
          <Brain className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">No Fine-Tuning Jobs</h3>
          <p className="text-gray-400 mb-4">
            {filter === 'all'
              ? "You haven't created any fine-tuning jobs yet."
              : `No ${filter} jobs found.`}
          </p>
          {filter === 'all' && (
            <Button
              onClick={() => setShowModal(true)}
              className="bg-purple-500 hover:bg-purple-600 text-white"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create Your First Job
            </Button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredJobs.map(job => (
            <JobCard
              key={job.id}
              job={job}
              onRefresh={handleRefresh}
              onViewLogs={handleViewLogs}
              onCancel={handleCancel}
              onDeploy={handleDeploy}
              onDownload={handleDownload}
            />
          ))}
        </div>
      )}

      {/* Fine-Tuning Modal */}
      <FineTuningModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        onSuccess={(job) => {
          fetchJobs();
          setShowModal(false);
        }}
      />

      {/* Logs Modal */}
      <LogsModal
        job={selectedJob}
        isOpen={showLogs}
        onClose={() => setShowLogs(false)}
      />

      {/* Deploy Modal */}
      <DeployModal
        job={selectedJob}
        isOpen={showDeploy}
        onClose={() => setShowDeploy(false)}
        onSuccess={(data) => {
          alert(`Deployment started! Instance: ${data.instance_name || 'Creating...'}`);
          fetchJobs();
        }}
      />
    </div>
  );
}
