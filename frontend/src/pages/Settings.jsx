import { useState, useEffect } from 'react';
import { Camera, Settings2, Trash2, Plus, Terminal } from 'lucide-react';

export default function Settings() {
  const [cameras, setCameras] = useState([]);
  const [newCamId, setNewCamId] = useState('');
  const [newCamUrl, setNewCamUrl] = useState('');
  
  const fetchCameras = () => {
    fetch('http://localhost:8000/api/cameras')
      .then(res => res.json())
      .then(data => setCameras(data.cameras || []));
  };

  useEffect(() => {
    fetchCameras();
  }, []);

  const addCamera = async (e) => {
    e.preventDefault();
    if(!newCamId || !newCamUrl) return;
    
    try {
      const res = await fetch('http://localhost:8000/api/cameras', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ camera_id: newCamId, source: newCamUrl })
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        alert(`Error: ${data.detail || 'Failed to add camera'}`);
      } else {
        setNewCamId('');
        setNewCamUrl('');
        fetchCameras();
      }
    } catch (err) {
      alert(`Error connecting to server: ${err.message}`);
    }
  };

  const removeCamera = async (id) => {
    await fetch(`http://localhost:8000/api/cameras/${id}`, { method: 'DELETE' });
    fetchCameras();
  };

  return (
    <div className="max-w-4xl mx-auto py-6 animation-fade-in space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">System Configuration</h1>
        <p className="text-slate-500 text-sm mt-1">Manage external cameras and core facial recognition settings.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        
        {/* Camera Settings */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm overflow-hidden">
          <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 flex items-center gap-2">
            <Camera className="w-5 h-5 text-primary" />
            <h2 className="font-semibold text-slate-800 dark:text-slate-100">Camera Feeds</h2>
          </div>
          
          <div className="p-4 border-b border-slate-200 dark:border-slate-800">
            <form onSubmit={addCamera} className="space-y-3">
              <div>
                <input 
                  type="text" placeholder="Camera ID (e.g. Hallway-1)" 
                  value={newCamId} onChange={e=>setNewCamId(e.target.value)}
                  className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-300 rounded focus:ring-2 focus:ring-primary outline-none dark:bg-slate-800 dark:border-slate-700 dark:text-white"
                />
              </div>
              <div className="flex gap-2">
                <input 
                  type="text" placeholder="Source (0 for local, or http://...)" 
                  value={newCamUrl} onChange={e=>setNewCamUrl(e.target.value)}
                  className="flex-1 px-3 py-2 text-sm bg-slate-50 border border-slate-300 rounded focus:ring-2 focus:ring-primary outline-none dark:bg-slate-800 dark:border-slate-700 dark:text-white"
                />
                <button type="submit" className="bg-slate-900 dark:bg-white text-white dark:text-slate-900 px-3 py-2 rounded font-medium text-sm flex items-center">
                  <Plus className="w-4 h-4" /> Add
                </button>
              </div>
            </form>
          </div>

          <div className="p-0">
            {cameras.length === 0 && <div className="p-6 text-center text-sm text-slate-500">No active cameras attached.</div>}
            <ul className="divide-y divide-slate-100 dark:divide-slate-800">
              {cameras.map(c => (
                <li key={c.id} className="p-4 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-800/50">
                  <div>
                    <div className="font-medium text-sm dark:text-slate-200">{c.id}</div>
                    <div className="text-xs text-slate-500 font-mono mt-0.5">{c.source}</div>
                  </div>
                  <button onClick={() => removeCamera(c.id)} className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Model Settings */}
        <div className="space-y-8">
          
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm overflow-hidden">
            <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 flex items-center gap-2">
              <Settings2 className="w-5 h-5 text-primary" />
              <h2 className="font-semibold text-slate-800 dark:text-slate-100">Recognition Threshold (Cosine)</h2>
            </div>
            <div className="p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium dark:text-slate-300">0.60 (Strict)</span>
              </div>
              <input type="range" min="0" max="100" defaultValue="60" className="w-full accent-primary" />
              <p className="text-xs text-slate-500 mt-3">Higher threshold prevents false positives but may reject slight facial variations. Currently set via backend const.</p>
            </div>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm overflow-hidden">
            <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 flex items-center gap-2">
              <Terminal className="w-5 h-5 text-primary" />
              <h2 className="font-semibold text-slate-800 dark:text-slate-100">System Information</h2>
            </div>
            <div className="p-4 font-mono text-xs text-slate-600 dark:text-slate-400 space-y-2">
              <div className="flex justify-between border-b border-slate-100 dark:border-slate-800 pb-2"><span>OpenCV Version:</span> <span className="font-semibold text-slate-900 dark:text-slate-200">4.10.0</span></div>
              <div className="flex justify-between border-b border-slate-100 dark:border-slate-800 pb-2"><span>InsightFace ONNX:</span> <span className="font-semibold text-slate-900 dark:text-slate-200">buffalo_l</span></div>
              <div className="flex justify-between pb-1"><span>FastAPI Backend:</span> <span className="text-emerald-500 font-semibold">Running (port 8000)</span></div>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
