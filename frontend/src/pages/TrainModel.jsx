import { useState } from 'react';
import { BrainCircuit, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

export default function TrainModel() {
  const [status, setStatus] = useState('idle'); // idle, training, completed, error
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState([]);

  const startTraining = async () => {
    setStatus('training');
    setProgress(0);
    setLogs(['Initializing training pipeline...', 'Verifying ArcFace model weights...']);
    
    // Simulate training progress for the visualizer
    const interval = setInterval(() => {
      setProgress(p => {
        if (p >= 90) {
          clearInterval(interval);
          return 90;
        }
        return p + Math.floor(Math.random() * 15);
      });
      setLogs(curr => [...curr, `Extracting embeddings from batch ${Math.floor(Math.random() * 10)}...`]);
    }, 600);

    try {
      const response = await fetch('http://localhost:8000/api/model/train', { method: 'POST' });
      const data = await response.json();
      
      clearInterval(interval);
      setProgress(100);
      
      if (response.ok) {
        setStatus('completed');
        setLogs(curr => [...curr, `✓ ${data.message}`, 'Training pipeline completed successfully.']);
      } else {
        setStatus('error');
        setLogs(curr => [...curr, '✗ Target backend reported an error.']);
      }
    } catch (err) {
      clearInterval(interval);
      setStatus('error');
      setLogs(curr => [...curr, '✗ Network error communicating with server.']);
    }
  };

  return (
    <div className="h-full flex flex-col items-center justify-center py-12 max-w-4xl mx-auto animation-fade-in">
      <div className="text-center mb-12">
        <div className="mx-auto w-20 h-20 bg-primary/10 dark:bg-primary/20 text-primary dark:text-primary-hover rounded-2xl flex items-center justify-center mb-6 shadow-sm border border-primary/20">
          <BrainCircuit className="w-10 h-10" />
        </div>
        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">Model Training</h1>
        <p className="text-slate-500 dark:text-slate-400 mt-2 max-w-lg mx-auto">
          Re-compute and cache facial embeddings for all active students. Run this after bulk importing photos.
        </p>
      </div>

      <div className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm rounded-2xl p-8">
        
        {status === 'idle' && (
          <div className="flex justify-center py-12">
            <button 
              onClick={startTraining}
              className="bg-primary hover:bg-primary-hover text-white text-lg font-medium px-10 py-5 rounded-full shadow-[0_0_40px_rgba(170,59,255,0.3)] transition-all hover:scale-105 hover:shadow-[0_0_60px_rgba(170,59,255,0.4)] flex items-center gap-3"
            >
              <BrainCircuit className="w-6 h-6" />
              Start Training Pipeline
            </button>
          </div>
        )}

        {status !== 'idle' && (
          <div className="space-y-8">
            <div className="flex items-center justify-between text-sm font-medium mb-2">
              <span className="text-slate-600 dark:text-slate-300">
                Status: {status === 'training' ? <span className="text-blue-500">Processing...</span> : 
                         status === 'completed' ? <span className="text-emerald-500">Completed</span> : 
                         <span className="text-red-500">Failed</span>}
              </span>
              <span className="text-slate-900 dark:text-slate-100">{Math.min(progress, 100)}%</span>
            </div>
            
            <div className="h-4 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
              <div 
                className={`h-full rounded-full transition-all duration-300 ease-out ${status === 'error' ? 'bg-red-500' : status === 'completed' ? 'bg-emerald-500' : 'bg-primary relative overflow-hidden'}`}
                style={{ width: `${Math.min(progress, 100)}%` }}
              >
                {status === 'training' && (
                  <div className="absolute inset-0 bg-white/20 w-full animate-[shimmer_2s_infinite]" style={{ transform: 'skewX(-20deg)' }}></div>
                )}
              </div>
            </div>

            <div className="bg-slate-950 rounded-xl p-4 font-mono text-sm h-64 overflow-y-auto border border-slate-800">
              <div className="text-emerald-400 mb-2">$ initiating insightface extraction loop</div>
              {logs.map((log, i) => (
                <div key={i} className="text-slate-300 mb-1">
                  <span className="text-slate-600 mr-2">[{new Date().toLocaleTimeString()}]</span>
                  {log}
                </div>
              ))}
              {status === 'training' && (
                <div className="text-slate-500 flex items-center gap-2 mt-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  working...
                </div>
              )}
            </div>

            {status === 'completed' && (
              <div className="flex justify-center pt-4">
                <button 
                  onClick={() => { setStatus('idle'); setProgress(0); setLogs([]); }}
                  className="px-6 py-2 rounded-lg font-medium border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                >
                  Close Visualizer
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
