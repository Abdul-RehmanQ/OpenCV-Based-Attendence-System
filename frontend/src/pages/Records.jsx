import { useState, useEffect } from 'react';
import { Database, Download, Search, Filter } from 'lucide-react';

export default function Records() {
  const [records, setRecords] = useState([]);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetch('http://localhost:8000/api/records')
      .then(res => res.json())
      .then(data => setRecords(data.records || []));
  }, []);

  const filtered = records.filter(r => 
    r.name?.toLowerCase().includes(search.toLowerCase()) || 
    r.rollnumber?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="h-full flex flex-col animation-fade-in">
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight flex items-center gap-2">
            <Database className="w-7 h-7 text-primary" />
            Attendance Records
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">View, filter, and export finalized multi-camera attendance data.</p>
        </div>
        <div className="flex gap-2">
          <button className="flex items-center gap-2 px-4 py-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-lg text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors">
            <Filter className="w-4 h-4" /> Filter
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-slate-900 hover:bg-slate-800 dark:bg-slate-100 dark:hover:bg-white text-white dark:text-slate-900 rounded-lg text-sm font-medium transition-colors">
            <Download className="w-4 h-4" /> Export CSV
          </button>
        </div>
      </div>

      <div className="flex-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm flex flex-col overflow-hidden">
        
        {/* Toolbar */}
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center gap-4 bg-slate-50 dark:bg-slate-800/50">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input 
              type="text" 
              placeholder="Search by student name or ID..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary dark:text-slate-200"
            />
          </div>
        </div>

        {/* Table */}
        <div className="flex-1 overflow-auto">
          <table className="w-full text-left border-collapse">
            <thead className="sticky top-0 bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 z-10 shadow-sm">
              <tr className="text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold">
                <th className="px-6 py-4">Student</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Date finalizing</th>
                <th className="px-6 py-4">Presence (sec)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800/50">
              {filtered.length === 0 && (
                <tr>
                  <td colSpan="4" className="px-6 py-12 text-center text-slate-500">
                    No finalized attendance records found. Stop an active session to generate records.
                  </td>
                </tr>
              )}
              {filtered.map((r, i) => (
                <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors">
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-slate-900 dark:text-slate-200">{r.name}</div>
                    <div className="text-xs text-slate-500">{r.rollnumber} | Class {r.class_id}</div>
                  </td>
                  <td className="px-6 py-4">
                    {r.status === 'present' ? (
                      <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700 border border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/20">Present</span>
                    ) : r.status === 'late' ? (
                      <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-700 border border-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/20">Late</span>
                    ) : (
                      <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700 border border-red-200 dark:bg-red-500/10 dark:text-red-400 dark:border-red-500/20 capitalize">{r.status}</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-600 dark:text-slate-300">{new Date(r.finalized_at).toLocaleString()}</td>
                  <td className="px-6 py-4 text-sm text-slate-600 dark:text-slate-300 font-mono">
                    {r.present_seconds} / {r.required_seconds}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {/* Pagination mock */}
        <div className="p-4 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-sm text-slate-500 bg-white dark:bg-slate-900">
          <span>Showing {filtered.length} entries</span>
          <div className="flex gap-1">
            <button className="px-3 py-1 rounded border border-slate-300 dark:border-slate-700 disabled:opacity-50">Prev</button>
            <button className="px-3 py-1 rounded border border-slate-300 bg-slate-100 dark:bg-slate-800 dark:border-slate-700 font-medium">1</button>
            <button className="px-3 py-1 rounded border border-slate-300 dark:border-slate-700 disabled:opacity-50">Next</button>
          </div>
        </div>

      </div>
    </div>
  );
}
