import { useState, useEffect, useRef } from 'react';
import { Camera, Play, Square, Users, Clock, AlertTriangle } from 'lucide-react';

export default function Capture() {
  const [cameras, setCameras] = useState([]);
  const [activeCam, setActiveCam] = useState(null);
  const [classes, setClasses] = useState([]);
  const [selectedClass, setSelectedClass] = useState("");
  const [sessionActive, setSessionActive] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    // Fetch available classes
    fetch('http://localhost:8000/api/classes')
      .then(res => res.json())
      .then(data => {
        if (data.classes && data.classes.length > 0) {
          setClasses(data.classes);
          setSelectedClass(data.classes[0].id);
        }
      });

    // Fetch cameras
    fetch('http://localhost:8000/api/cameras')
      .then(res => res.json())
      .then(data => {
        if (data.cameras) {
          setCameras(data.cameras);
          if (data.cameras.length > 0) {
            setActiveCam(data.cameras[0].id);
          }
        }
      });
  }, []);

  // Polling dummy logs or actual logs could be implemented via Websocket. 
  // For now, we simulate the log feed pulling from the backend periodically if active.
  useEffect(() => {
    let interval;
    if (sessionActive && sessionId) {
      interval = setInterval(() => {
        // In a full websocket setup, this would be pushed. We mock the front-end visual array here.
        fetch('http://localhost:8000/api/records')
          .then(res => res.json())
          .then(data => {
            // Update logs based on latest
          })
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [sessionActive, sessionId]);

  const startSession = async () => {
    if (!selectedClass || !activeCam) return;
    
    try {
      const res = await fetch('http://localhost:8000/api/sessions/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          class_id: parseInt(selectedClass),
          duration_seconds: 3600,
          camera_id: activeCam
        })
      });
      const data = await res.json();
      if (res.ok) {
        setSessionId(data.session_id);
        setSessionActive(true);
        // Add a mock log to start
        setLogs([{ time: new Date().toLocaleTimeString(), text: 'System tracking started. Monitoring doorway.', type: 'info' }]);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const stopSession = async () => {
    if (!sessionId) return;
    try {
      await fetch(`http://localhost:8000/api/sessions/${sessionId}/finalize`, { method: 'POST' });
      setSessionActive(false);
      setSessionId(null);
      setLogs(curr => [{ time: new Date().toLocaleTimeString(), text: 'Session finalized.', type: 'info' }, ...curr]);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="h-full flex flex-col xl:flex-row gap-6 animation-fade-in">
      
      {/* Main Camera View */}
      <div className="flex-[2] flex flex-col gap-4">
        
        <div className="flex items-center justify-between bg-white dark:bg-slate-900 p-4 rounded-xl shadow-sm border border-slate-200 dark:border-slate-800">
          <div className="flex items-center gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1 block">Live Camera Feed</label>
              <select 
                value={activeCam || ''} 
                onChange={(e) => setActiveCam(e.target.value)}
                className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-sm font-medium outline-none focus:ring-2 focus:ring-primary"
              >
                {cameras.length === 0 && <option value="">No cameras found</option>}
                {cameras.map(c => <option key={c.id} value={c.id}>Camera: {c.id}</option>)}
              </select>
            </div>
            
            <div className="h-8 w-px bg-slate-200 dark:bg-slate-700 mx-2"></div>
            
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1 block">Target Class</label>
              <select 
                value={selectedClass} 
                onChange={(e) => setSelectedClass(e.target.value)}
                disabled={sessionActive}
                className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-sm font-medium outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
              >
                {classes.length === 0 && <option value="">No classes available</option>}
                {classes.map(c => <option key={c.id} value={c.id}>{c.class_name}</option>)}
              </select>
            </div>
          </div>

          <div>
            {!sessionActive ? (
              <button 
                onClick={startSession}
                disabled={!selectedClass || !activeCam}
                className="bg-emerald-500 hover:bg-emerald-600 text-white px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors disabled:opacity-50"
              >
                <Play className="w-4 h-4 fill-current" /> Initialize Tracking
              </button>
            ) : (
              <button 
                onClick={stopSession}
                className="bg-red-500 hover:bg-red-600 text-white px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors"
              >
                <Square className="w-4 h-4 fill-current" /> Stop & Finalize
              </button>
            )}
          </div>
        </div>

        {/* Video Container */}
        <div className="flex-1 bg-black rounded-xl overflow-hidden shadow-sm relative border border-slate-200 dark:border-slate-800 flex items-center justify-center">
          {sessionActive && activeCam ? (
            <img 
              src={`http://localhost:8000/api/video_feed/${activeCam}`} 
              alt="Live Cam" 
              className="w-full h-full object-contain"
            />
          ) : (
            <div className="text-center text-slate-500 flex flex-col items-center">
              <Camera className="w-16 h-16 mb-4 opacity-50" />
              <p className="font-medium text-lg">Camera is Offline</p>
              <p className="text-sm mt-1">Select a class and click Initialize Tracking to begin.</p>
            </div>
          )}
          
          {sessionActive && (
            <div className="absolute top-4 left-4 bg-black/60 backdrop-blur-md text-white px-3 py-1.5 rounded-full text-xs font-medium flex items-center gap-2 border border-white/10 shadow-lg">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
              LIVE RECORDING
            </div>
          )}
        </div>

      </div>

      {/* Right Sidebar: Real-time logs */}
      <div className="flex-1 max-w-sm xl:max-w-md bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col overflow-hidden">
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
          <h2 className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Users className="w-5 h-5 text-primary" />
            Live Recognition Log
          </h2>
          {sessionActive && (
             <div className="mt-2 text-xs font-medium text-slate-500 dark:text-slate-400 flex items-center gap-1">
               <Clock className="w-3 h-3" /> Session {sessionId} active
             </div>
          )}
        </div>
        
        <div className="flex-1 overflow-auto p-4 space-y-3 bg-slate-50 dark:bg-slate-900">
          {!sessionActive && logs.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-slate-400">
              <AlertTriangle className="w-8 h-8 mb-2 opacity-50" />
              <p className="text-sm">Log will populate when session starts.</p>
            </div>
          )}
          
          {logs.map((log, i) => (
            <div key={i} className="bg-white dark:bg-slate-800 p-3 rounded-lg border border-slate-100 dark:border-slate-700 shadow-sm flex gap-3 animate-in fade-in slide-in-from-right-4">
              <div className="text-xs font-mono text-slate-400 mt-0.5 whitespace-nowrap">{log.time}</div>
              <div className="text-sm font-medium text-slate-700 dark:text-slate-200">{log.text}</div>
            </div>
          ))}

          {/* Dummy entries for visual example of how it looks during streaming */}
          {sessionActive && (
            <>
              <div className="bg-white dark:bg-slate-800 p-3 rounded-lg border-l-4 border-l-emerald-500 border border-slate-100 dark:border-slate-700 shadow-sm flex justify-between items-center animate-in fade-in slide-in-from-right-4 opacity-50">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-emerald-100 dark:bg-emerald-900/50 rounded-full flex items-center justify-center text-emerald-600 dark:text-emerald-400 font-bold text-xs">JD</div>
                  <span className="text-sm font-semibold dark:text-slate-200">John Doe</span>
                </div>
                <div className="text-xs font-mono text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/30 px-2 py-1 rounded">98.2%</div>
              </div>
            </>
          )}
        </div>
      </div>
      
    </div>
  );
}
