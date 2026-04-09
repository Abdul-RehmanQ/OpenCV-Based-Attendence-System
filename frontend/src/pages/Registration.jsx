import { useState, useRef, useCallback } from 'react';
import { Camera, Upload, CheckCircle2, AlertCircle } from 'lucide-react';

export default function Registration() {
  const [step, setStep] = useState(1); // 1 = Details, 2 = Camera, 3 = Confirm
  const [formData, setFormData] = useState({ name: '', rollnumber: '', department: '' });
  const [imageBlob, setImageBlob] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [status, setStatus] = useState(null);
  
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (err) {
      console.error("Camera access denied", err);
      setStatus({ type: 'error', text: 'Camera access denied. Please grant permission.' });
    }
  };

  const stopCamera = () => {
    const stream = videoRef.current?.srcObject;
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
    }
  };

  const captureFace = () => {
    if (!videoRef.current || !canvasRef.current) return;
    
    const context = canvasRef.current.getContext('2d');
    canvasRef.current.width = videoRef.current.videoWidth;
    canvasRef.current.height = videoRef.current.videoHeight;
    context.drawImage(videoRef.current, 0, 0);
    
    canvasRef.current.toBlob((blob) => {
      setImageBlob(blob);
      setImagePreview(URL.createObjectURL(blob));
      stopCamera();
      setStep(3);
    }, 'image/jpeg', 0.9);
  };

  const submitRegistration = async () => {
    setIsSubmitting(true);
    setStatus(null);
    
    const fd = new FormData();
    fd.append('name', formData.name);
    fd.append('rollnumber', formData.rollnumber);
    fd.append('department', formData.department);
    if (imageBlob) {
      fd.append('file', imageBlob, 'capture.jpg');
    }

    try {
      const response = await fetch('http://localhost:8000/api/students', {
        method: 'POST',
        body: fd
      });
      const data = await response.json();
      
      if (response.ok) {
        setStatus({ type: 'success', text: 'Student registered successfully!' });
        setTimeout(() => {
          setStep(1);
          setFormData({ name: '', rollnumber: '', department: '' });
          setImageBlob(null);
          setImagePreview(null);
          setStatus(null);
        }, 3000);
      } else {
        setStatus({ type: 'error', text: data.detail || 'Failed to register student.' });
      }
    } catch (err) {
      setStatus({ type: 'error', text: 'Network error communicating with server.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto py-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wide">Student Enrollment</h1>
        <p className="text-slate-500">Register new students into the facial recognition database.</p>
      </div>

      {/* Stepper */}
      <div className="flex items-center mb-8">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex items-center">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${step >= i ? 'bg-primary text-white' : 'bg-slate-200 dark:bg-slate-800 text-slate-500'}`}>
              {i}
            </div>
            {i !== 3 && <div className={`w-24 h-1 mx-2 rounded ${step > i ? 'bg-primary' : 'bg-slate-200 dark:bg-slate-800'}`} />}
          </div>
        ))}
      </div>

      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm p-6">
        
        {status && (
          <div className={`mb-6 p-4 rounded-lg flex items-center gap-3 ${status.type === 'success' ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20' : 'bg-red-50 dark:bg-red-500/10 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-500/20'}`}>
            {status.type === 'success' ? <CheckCircle2 className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
            <span className="font-medium text-sm">{status.text}</span>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-4 animate-in fade-in">
            <h3 className="text-lg font-medium border-b border-slate-100 dark:border-slate-800 pb-2">Student Details</h3>
            
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Full Name</label>
              <input 
                type="text" 
                className="w-full px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all dark:text-slate-200"
                value={formData.name}
                onChange={e => setFormData({...formData, name: e.target.value})}
                placeholder="John Doe"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Roll Number / ID</label>
                <input 
                  type="text" 
                  className="w-full px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all dark:text-slate-200"
                  value={formData.rollnumber}
                  onChange={e => setFormData({...formData, rollnumber: e.target.value})}
                  placeholder="CS-2024-001"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Department</label>
                <input 
                  type="text" 
                  className="w-full px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all dark:text-slate-200"
                  value={formData.department}
                  onChange={e => setFormData({...formData, department: e.target.value})}
                  placeholder="Computer Science"
                />
              </div>
            </div>

            <div className="mt-8 pt-4 flex justify-end">
              <button 
                onClick={() => {
                  setStep(2);
                  startCamera();
                }}
                disabled={!formData.name || !formData.rollnumber}
                className="bg-primary hover:bg-primary-hover text-white px-6 py-2 rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                Continue to Camera
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4 animate-in fade-in">
            <h3 className="text-lg font-medium border-b border-slate-100 dark:border-slate-800 pb-2">Capture Face Data</h3>
            
            <div className="bg-slate-100 dark:bg-slate-800 rounded-lg overflow-hidden relative" style={{ aspectRatio: '4/3' }}>
              <video 
                ref={videoRef} 
                autoPlay 
                playsInline 
                muted 
                className="w-full h-full object-cover"
              />
              <canvas ref={canvasRef} className="hidden" />
              
              <div className="absolute inset-0 border-2 border-primary/50 m-8 rounded-3xl pointer-events-none border-dashed" />
              
              <div className="absolute bottom-4 left-0 right-0 flex justify-center">
                <button 
                  onClick={captureFace}
                  className="bg-white text-primary rounded-full p-4 hover:scale-105 transition-transform shadow-lg"
                >
                  <Camera className="w-8 h-8" />
                </button>
              </div>
            </div>
            
            <div className="bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400 p-3 rounded-lg text-sm flex gap-2">
              <AlertCircle className="w-5 h-5 shrink-0" />
              Look directly at the camera. Ensure you are in a well-lit environment.
            </div>

            <div className="mt-8 pt-4 flex justify-between">
              <button onClick={() => { setStep(1); stopCamera(); }} className="text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 font-medium">Back</button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-6 text-center animate-in fade-in">
            <h3 className="text-lg font-medium">Review & Save</h3>
            
            <div className="w-48 h-48 mx-auto rounded-full overflow-hidden border-4 border-primary/20">
              {imagePreview && (
                <img src={imagePreview} alt="Captured preview" className="w-full h-full object-cover" />
              )}
            </div>

            <div className="text-left bg-slate-50 dark:bg-slate-800/50 p-4 rounded-lg inline-block text-sm">
              <p><span className="text-slate-500 dark:text-slate-400">Name:</span> <span className="font-medium dark:text-slate-200">{formData.name}</span></p>
              <p><span className="text-slate-500 dark:text-slate-400">Roll No:</span> <span className="font-medium dark:text-slate-200">{formData.rollnumber}</span></p>
            </div>

            <div className="pt-6 flex justify-center gap-4 border-t border-slate-100 dark:border-slate-800">
              <button 
                onClick={() => { setStep(2); startCamera(); }}
                disabled={isSubmitting}
                className="px-6 py-2 rounded-lg font-medium border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
              >
                Retake Photo
              </button>
              <button 
                onClick={submitRegistration}
                disabled={isSubmitting}
                className="bg-primary hover:bg-primary-hover text-white px-8 py-2 rounded-lg font-medium transition-colors flex items-center gap-2"
              >
                {isSubmitting ? (
                  <span className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></span>
                ) : (
                  <Upload className="w-5 h-5" />
                )}
                Save Student
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
