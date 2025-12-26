import { useState, useEffect } from 'react';
import {
  Brain,
  Upload,
  Link,
  Database,
  Settings2,
  Play,
  Loader2,
  Info,
  Check,
  ChevronRight,
  ChevronLeft,
  Cpu,
  Zap,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Button } from './ui/button';
import { Label } from './ui/label';
import { Input } from './ui/input';
import { Slider } from './ui/slider';

// Supported models
const MODELS = [
  { id: 'unsloth/llama-3-8b-bnb-4bit', name: 'Llama 3 8B', vram: '16GB', desc: 'Meta\'s latest 8B parameter model' },
  { id: 'unsloth/mistral-7b-bnb-4bit', name: 'Mistral 7B', vram: '12GB', desc: 'Fast and efficient 7B model' },
  { id: 'unsloth/gemma-7b-bnb-4bit', name: 'Gemma 7B', vram: '12GB', desc: 'Google\'s open-source 7B model' },
  { id: 'unsloth/Qwen2-7B-bnb-4bit', name: 'Qwen 2 7B', vram: '12GB', desc: 'Alibaba\'s multilingual model' },
  { id: 'unsloth/Phi-3-mini-4k-instruct-bnb-4bit', name: 'Phi-3 Mini', vram: '8GB', desc: 'Microsoft\'s compact but powerful model' },
];

// GPU options
const GPU_OPTIONS = [
  { value: 'RTX4090', label: 'RTX 4090', vram: '24GB', price: '~$0.80/hr' },
  { value: 'A100', label: 'A100 40GB', vram: '40GB', price: '~$1.50/hr' },
  { value: 'A100-80GB', label: 'A100 80GB', vram: '80GB', price: '~$2.50/hr' },
  { value: 'H100', label: 'H100 80GB', vram: '80GB', price: '~$3.50/hr' },
];

// Dataset format options
const FORMAT_OPTIONS = [
  { value: 'alpaca', label: 'Alpaca', desc: 'instruction, input, output' },
  { value: 'sharegpt', label: 'ShareGPT', desc: 'conversations array' },
];

export default function FineTuningModal({ isOpen, onClose, onSuccess }) {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Step 1: Model selection
  const [baseModel, setBaseModel] = useState(MODELS[0].id);

  // Step 2: Dataset
  const [datasetSource, setDatasetSource] = useState('upload');
  const [datasetPath, setDatasetPath] = useState('');
  const [datasetFormat, setDatasetFormat] = useState('alpaca');
  const [uploadedFile, setUploadedFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  // Step 3: Configuration
  const [jobName, setJobName] = useState('');
  const [gpuType, setGpuType] = useState('A100');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [config, setConfig] = useState({
    lora_rank: 16,
    lora_alpha: 16,
    learning_rate: 0.0002,
    epochs: 1,
    batch_size: 2,
    max_seq_length: 2048,
  });

  // Reset on modal open
  useEffect(() => {
    if (isOpen) {
      setStep(1);
      setError(null);
      setJobName('');
      setDatasetPath('');
      setUploadedFile(null);
    }
  }, [isOpen]);

  // Handle file upload
  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploadedFile(file);
    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const token = localStorage.getItem('auth_token');
      const res = await fetch('/api/v1/finetune/jobs/upload-dataset', {
        method: 'POST',
        body: formData,
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Upload failed');
      }

      const data = await res.json();
      setDatasetPath(data.dataset_path);
    } catch (err) {
      setError('Failed to upload dataset: ' + err.message);
      setUploadedFile(null);
    } finally {
      setUploading(false);
    }
  };

  // Launch fine-tuning job
  const handleLaunch = async () => {
    if (!jobName.trim()) {
      setError('Please enter a job name');
      return;
    }
    if (!datasetPath) {
      setError('Please upload a dataset or provide a URL');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch('/api/v1/finetune/jobs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          name: jobName,
          base_model: baseModel,
          dataset_source: datasetSource,
          dataset_path: datasetPath,
          dataset_format: datasetFormat,
          config: config,
          gpu_type: gpuType,
          num_gpus: 1,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to create job');
      }

      const job = await res.json();
      onSuccess && onSuccess(job);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Get selected model details
  const selectedModel = MODELS.find(m => m.id === baseModel);

  // Step navigation
  const canProceed = () => {
    switch (step) {
      case 1: return !!baseModel;
      case 2: return !!datasetPath;
      case 3: return !!jobName.trim();
      default: return true;
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl bg-[#1a1f2e] border-gray-700 text-white">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <Brain className="w-5 h-5 text-purple-400" />
            Fine-Tune Model with Unsloth
          </DialogTitle>
          <DialogDescription className="text-gray-400">
            Step {step} of 4: {
              step === 1 ? 'Select Base Model' :
              step === 2 ? 'Upload Dataset' :
              step === 3 ? 'Configure Job' :
              'Review & Launch'
            }
          </DialogDescription>
        </DialogHeader>

        {/* Progress bar */}
        <div className="flex gap-1 mt-2">
          {[1, 2, 3, 4].map(s => (
            <div
              key={s}
              className={`h-1 flex-1 rounded-full transition-colors ${
                s <= step ? 'bg-purple-500' : 'bg-gray-700'
              }`}
            />
          ))}
        </div>

        <div className="space-y-5 py-4 min-h-[300px]">
          {error && (
            <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-3 flex items-start gap-2">
              <Info className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {/* Step 1: Model Selection */}
          {step === 1 && (
            <div className="space-y-4">
              <Label className="text-base font-medium flex items-center gap-2">
                <Cpu className="w-4 h-4 text-purple-400" />
                Select Base Model
              </Label>
              <p className="text-sm text-gray-400">
                Choose a pre-trained model to fine-tune. All models use 4-bit quantization for 80% less VRAM.
              </p>

              <div className="space-y-2">
                {MODELS.map(model => (
                  <div
                    key={model.id}
                    onClick={() => setBaseModel(model.id)}
                    className={`p-4 rounded-lg border cursor-pointer transition-all ${
                      baseModel === model.id
                        ? 'border-purple-500 bg-purple-500/10'
                        : 'border-gray-700 hover:border-gray-600 bg-gray-800/50'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-medium text-white">{model.name}</h4>
                        <p className="text-sm text-gray-400">{model.desc}</p>
                      </div>
                      <div className="text-right">
                        <span className="text-xs bg-gray-700 px-2 py-1 rounded text-gray-300">
                          Min {model.vram} VRAM
                        </span>
                        {baseModel === model.id && (
                          <Check className="w-5 h-5 text-purple-400 mt-1 ml-auto" />
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Step 2: Dataset */}
          {step === 2 && (
            <div className="space-y-4">
              <Label className="text-base font-medium flex items-center gap-2">
                <Database className="w-4 h-4 text-purple-400" />
                Dataset
              </Label>

              {/* Source selection */}
              <div className="flex gap-2">
                <button
                  onClick={() => setDatasetSource('upload')}
                  className={`flex-1 p-3 rounded-lg border flex items-center justify-center gap-2 transition-all ${
                    datasetSource === 'upload'
                      ? 'border-purple-500 bg-purple-500/10 text-purple-400'
                      : 'border-gray-700 hover:border-gray-600 text-gray-400'
                  }`}
                >
                  <Upload className="w-4 h-4" />
                  Upload File
                </button>
                <button
                  onClick={() => setDatasetSource('url')}
                  className={`flex-1 p-3 rounded-lg border flex items-center justify-center gap-2 transition-all ${
                    datasetSource === 'url'
                      ? 'border-purple-500 bg-purple-500/10 text-purple-400'
                      : 'border-gray-700 hover:border-gray-600 text-gray-400'
                  }`}
                >
                  <Link className="w-4 h-4" />
                  URL
                </button>
              </div>

              {/* Upload section */}
              {datasetSource === 'upload' && (
                <div className="space-y-3">
                  <div
                    className={`border-2 border-dashed rounded-lg p-6 text-center transition-all ${
                      uploadedFile ? 'border-green-500/50 bg-green-500/5' : 'border-gray-700 hover:border-gray-600'
                    }`}
                  >
                    {uploading ? (
                      <div className="flex flex-col items-center gap-2">
                        <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
                        <span className="text-gray-400">Uploading...</span>
                      </div>
                    ) : uploadedFile ? (
                      <div className="flex flex-col items-center gap-2">
                        <Check className="w-8 h-8 text-green-400" />
                        <span className="text-white">{uploadedFile.name}</span>
                        <span className="text-xs text-gray-400">Upload successful</span>
                      </div>
                    ) : (
                      <label className="cursor-pointer">
                        <div className="flex flex-col items-center gap-2">
                          <Upload className="w-8 h-8 text-gray-400" />
                          <span className="text-gray-400">Click to upload JSON or JSONL file</span>
                          <span className="text-xs text-gray-500">Max 100MB</span>
                        </div>
                        <input
                          type="file"
                          accept=".json,.jsonl"
                          onChange={handleFileUpload}
                          className="hidden"
                        />
                      </label>
                    )}
                  </div>
                </div>
              )}

              {/* URL input */}
              {datasetSource === 'url' && (
                <div className="space-y-3">
                  <Input
                    placeholder="https://huggingface.co/datasets/... or direct JSON URL"
                    value={datasetPath}
                    onChange={(e) => setDatasetPath(e.target.value)}
                    className="bg-gray-800 border-gray-700 text-white"
                  />
                  <p className="text-xs text-gray-400">
                    Supports HuggingFace datasets and direct JSON file URLs
                  </p>
                </div>
              )}

              {/* Format selection */}
              <div className="space-y-2">
                <Label className="text-sm text-gray-400">Dataset Format</Label>
                <div className="flex gap-2">
                  {FORMAT_OPTIONS.map(fmt => (
                    <button
                      key={fmt.value}
                      onClick={() => setDatasetFormat(fmt.value)}
                      className={`flex-1 p-3 rounded-lg border text-left transition-all ${
                        datasetFormat === fmt.value
                          ? 'border-purple-500 bg-purple-500/10'
                          : 'border-gray-700 hover:border-gray-600'
                      }`}
                    >
                      <span className="font-medium text-white">{fmt.label}</span>
                      <p className="text-xs text-gray-400">{fmt.desc}</p>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Step 3: Configuration */}
          {step === 3 && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label className="text-base font-medium flex items-center gap-2">
                  <Settings2 className="w-4 h-4 text-purple-400" />
                  Job Configuration
                </Label>
              </div>

              {/* Job name */}
              <div className="space-y-2">
                <Label className="text-sm text-gray-400">Job Name</Label>
                <Input
                  placeholder="my-fine-tuned-model"
                  value={jobName}
                  onChange={(e) => setJobName(e.target.value)}
                  className="bg-gray-800 border-gray-700 text-white"
                />
              </div>

              {/* GPU selection */}
              <div className="space-y-2">
                <Label className="text-sm text-gray-400">GPU Type</Label>
                <div className="grid grid-cols-2 gap-2">
                  {GPU_OPTIONS.map(gpu => (
                    <button
                      key={gpu.value}
                      onClick={() => setGpuType(gpu.value)}
                      className={`p-3 rounded-lg border text-left transition-all ${
                        gpuType === gpu.value
                          ? 'border-purple-500 bg-purple-500/10'
                          : 'border-gray-700 hover:border-gray-600'
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <span className="font-medium text-white">{gpu.label}</span>
                        <span className="text-xs text-gray-400">{gpu.price}</span>
                      </div>
                      <span className="text-xs text-gray-400">{gpu.vram} VRAM</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Advanced settings toggle */}
              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="text-sm text-purple-400 hover:text-purple-300 flex items-center gap-1"
              >
                {showAdvanced ? 'Hide' : 'Show'} Advanced Settings
                <ChevronRight className={`w-4 h-4 transition-transform ${showAdvanced ? 'rotate-90' : ''}`} />
              </button>

              {/* Advanced settings */}
              {showAdvanced && (
                <div className="space-y-4 p-4 bg-gray-800/50 rounded-lg border border-gray-700">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label className="text-sm text-gray-400">LoRA Rank</Label>
                      <div className="flex items-center gap-3">
                        <Slider
                          value={[config.lora_rank]}
                          onValueChange={([v]) => setConfig({ ...config, lora_rank: v })}
                          min={4}
                          max={64}
                          step={4}
                          className="flex-1"
                        />
                        <span className="w-8 text-right text-white">{config.lora_rank}</span>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-sm text-gray-400">Epochs</Label>
                      <div className="flex items-center gap-3">
                        <Slider
                          value={[config.epochs]}
                          onValueChange={([v]) => setConfig({ ...config, epochs: v })}
                          min={1}
                          max={5}
                          step={1}
                          className="flex-1"
                        />
                        <span className="w-8 text-right text-white">{config.epochs}</span>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-sm text-gray-400">Batch Size</Label>
                      <div className="flex items-center gap-3">
                        <Slider
                          value={[config.batch_size]}
                          onValueChange={([v]) => setConfig({ ...config, batch_size: v })}
                          min={1}
                          max={8}
                          step={1}
                          className="flex-1"
                        />
                        <span className="w-8 text-right text-white">{config.batch_size}</span>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-sm text-gray-400">Max Seq Length</Label>
                      <div className="flex items-center gap-3">
                        <Slider
                          value={[config.max_seq_length]}
                          onValueChange={([v]) => setConfig({ ...config, max_seq_length: v })}
                          min={512}
                          max={4096}
                          step={256}
                          className="flex-1"
                        />
                        <span className="w-12 text-right text-white">{config.max_seq_length}</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 4: Review */}
          {step === 4 && (
            <div className="space-y-4">
              <Label className="text-base font-medium flex items-center gap-2">
                <Zap className="w-4 h-4 text-purple-400" />
                Review & Launch
              </Label>

              <div className="space-y-3 p-4 bg-gray-800/50 rounded-lg border border-gray-700">
                <div className="flex justify-between py-2 border-b border-gray-700">
                  <span className="text-gray-400">Job Name</span>
                  <span className="text-white font-medium">{jobName}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-gray-700">
                  <span className="text-gray-400">Base Model</span>
                  <span className="text-white">{selectedModel?.name}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-gray-700">
                  <span className="text-gray-400">Dataset</span>
                  <span className="text-white truncate max-w-[200px]">
                    {uploadedFile?.name || datasetPath.split('/').pop()}
                  </span>
                </div>
                <div className="flex justify-between py-2 border-b border-gray-700">
                  <span className="text-gray-400">GPU</span>
                  <span className="text-white">{GPU_OPTIONS.find(g => g.value === gpuType)?.label}</span>
                </div>
                <div className="flex justify-between py-2">
                  <span className="text-gray-400">Epochs</span>
                  <span className="text-white">{config.epochs}</span>
                </div>
              </div>

              <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-4">
                <div className="flex items-start gap-2">
                  <Info className="w-4 h-4 text-purple-400 mt-0.5" />
                  <div>
                    <p className="text-sm text-gray-300">
                      Fine-tuning will start immediately. You can monitor progress in the Fine-Tuning dashboard.
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      Estimated cost: {GPU_OPTIONS.find(g => g.value === gpuType)?.price} for GPU usage
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="flex justify-between">
          <div>
            {step > 1 && (
              <Button
                variant="ghost"
                onClick={() => setStep(step - 1)}
                disabled={loading}
                className="text-gray-400 hover:text-white"
              >
                <ChevronLeft className="w-4 h-4 mr-1" />
                Back
              </Button>
            )}
          </div>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              onClick={onClose}
              disabled={loading}
              className="text-gray-400 hover:text-white"
            >
              Cancel
            </Button>
            {step < 4 ? (
              <Button
                onClick={() => setStep(step + 1)}
                disabled={!canProceed()}
                className="bg-purple-500 hover:bg-purple-600 text-white"
              >
                Next
                <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            ) : (
              <Button
                onClick={handleLaunch}
                disabled={loading}
                className="bg-purple-500 hover:bg-purple-600 text-white gap-2"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
                {loading ? 'Launching...' : 'Launch Fine-Tuning'}
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
