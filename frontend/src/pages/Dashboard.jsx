import { useState, useEffect } from 'react';
import { Users, CheckCircle2, Target, Activity } from 'lucide-react';

function StatCard({ title, value, icon: Icon, trend }) {
  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl p-6 border border-slate-200 dark:border-slate-800 shadow-sm flex items-start gap-4">
      <div className="p-3 rounded-lg bg-primary/10 text-primary dark:bg-primary/20 dark:text-primary-hover">
        <Icon className="w-6 h-6" />
      </div>
      <div>
        <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{title}</p>
        <h3 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-1">{value}</h3>
        {trend && <p className="text-xs font-medium text-emerald-500 mt-1">{trend}</p>}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState({
    total_students: 0,
    total_classes: 0,
    total_sessions: 0,
    system_status: "Offline"
  });

  useEffect(() => {
    fetch('http://localhost:8000/api/stats')
      .then(res => res.json())
      .then(data => setStats(data))
      .catch(err => console.error(err));
  }, []);

  return (
    <div className="flex flex-col gap-6 h-full animation-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">Overview</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Real-time statistics from the attendance engine.</p>
      </div>

      {/* Widgets Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Total Students" value={stats.total_students} icon={Users} trend="+2 this week" />
        <StatCard title="Total Classes" value={stats.total_classes} icon={CheckCircle2} />
        <StatCard title="Recognition Accuracy" value="98.5%" icon={Target} trend="Optimal" />
        <StatCard title="System Status" value={stats.system_status} icon={Activity} />
      </div>

      {/* Table Section */}
      <div className="flex-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm flex flex-col overflow-hidden">
        <div className="px-6 py-5 border-b border-slate-200 dark:border-slate-800">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Recent Attendance Logs</h2>
        </div>
        <div className="p-0 overflow-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800 text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold">
                <th className="px-6 py-4">Name</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Time</th>
                <th className="px-6 py-4">Confidence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800/50">
              {/* Dummy data for preview before we wire records completely */}
              {[1, 2, 3, 4, 5].map((i) => (
                <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors">
                  <td className="px-6 py-4 text-sm font-medium text-slate-900 dark:text-slate-200 flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400 flex items-center justify-center font-bold text-xs">ST</div>
                    Student Name {i}
                  </td>
                  <td className="px-6 py-4">
                    <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20">Present</span>
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-500 dark:text-slate-400">09:{10 + i} AM</td>
                  <td className="px-6 py-4 text-sm font-mono text-slate-600 dark:text-slate-300">{(98 - i * 0.5).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
