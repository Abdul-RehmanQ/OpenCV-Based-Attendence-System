import { Play, ArrowRight, ShieldCheck, Zap, Users } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function Landing() {
  return (
    <div className="min-h-screen bg-slate-950 text-white font-sans overflow-hidden relative">
      
      {/* Background Ornaments */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-primary/20 blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-[-20%] right-[-10%] w-[40%] h-[40%] rounded-full bg-blue-600/20 blur-[100px] pointer-events-none"></div>
      
      <header className="px-8 py-6 flex items-center justify-between relative z-10 max-w-7xl mx-auto">
        <div className="flex items-center gap-2 font-bold text-2xl tracking-tighter">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-primary to-blue-500 flex items-center justify-center shadow-lg shadow-primary/20" />
          FaceAuth<span className="text-primary font-normal">AI</span>
        </div>
        <nav>
          <Link to="/" className="text-sm font-medium hover:text-primary transition-colors pr-6">Documentation</Link>
          <Link to="/" className="bg-white/10 hover:bg-white/20 px-5 py-2.5 rounded-full text-sm font-medium backdrop-blur-md transition-all border border-white/5">Sign In</Link>
        </nav>
      </header>

      <main className="max-w-7xl mx-auto px-8 pt-20 pb-32 relative z-10">
        
        <div className="text-center max-w-4xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary-hover text-xs font-semibold uppercase tracking-widest mb-8">
            <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
            Version 2.0 Live
          </div>
          
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-[1.1] mb-8">
            Automated Attendance with <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-blue-400">Vision AI</span>
          </h1>
          
          <p className="text-xl text-slate-400 mb-12 max-w-2xl mx-auto leading-relaxed">
            Eliminate manual registers. Track students across multiple hallways and classrooms in real-time with flawless facial recognition built on OpenCV.
          </p>
          
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/" className="bg-primary hover:bg-primary-hover text-white px-8 py-4 rounded-full font-medium transition-all hover:scale-105 shadow-[0_0_40px_rgba(170,59,255,0.4)] flex items-center gap-2 w-full sm:w-auto justify-center">
              Enter Admin System <ArrowRight className="w-5 h-5" />
            </Link>
            <button className="bg-white/5 hover:bg-white/10 text-white px-8 py-4 rounded-full font-medium border border-white/10 transition-all flex items-center gap-2 w-full sm:w-auto justify-center">
              <Play className="w-5 h-5" /> View Demo
            </button>
          </div>
        </div>

        {/* Feature grid */}
        <div className="grid md:grid-cols-3 gap-6 mt-32">
          
          <div className="bg-slate-900/50 backdrop-blur-sm border border-white/5 rounded-2xl p-8 hover:bg-slate-900/80 transition-colors">
            <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center text-blue-400 mb-6 border border-blue-500/20">
              <Zap className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-semibold mb-3">Real-time Processing</h3>
            <p className="text-slate-400 text-sm leading-relaxed">Our multi-threaded engine evaluates up to 10 cameras simultaneously capturing hundreds of face parameters per millisecond.</p>
          </div>

          <div className="bg-slate-900/50 backdrop-blur-sm border border-primary/20 rounded-2xl p-8 shadow-[0_0_30px_rgba(170,59,255,0.05)] relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center text-primary-hover mb-6 border border-primary/20 relative z-10">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-semibold mb-3 relative z-10">Flawless Accuracy</h3>
            <p className="text-slate-400 text-sm leading-relaxed relative z-10">Backed by InsightFace models yielding 99.8% precision, eliminating buddy punching and attendance fraud structurally.</p>
          </div>

          <div className="bg-slate-900/50 backdrop-blur-sm border border-white/5 rounded-2xl p-8 hover:bg-slate-900/80 transition-colors">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-400 mb-6 border border-emerald-500/20">
              <Users className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-semibold mb-3">Infinite Scalability</h3>
            <p className="text-slate-400 text-sm leading-relaxed">Whether screening 50 students in a lab or 50,000 across a campus, local edge JSON caching scales flawlessly.</p>
          </div>

        </div>

      </main>
    </div>
  );
}
