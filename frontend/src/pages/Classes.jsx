import { useState, useEffect } from 'react';
import { BookOpen, Plus, Search, BookMarked, Users, Hash } from 'lucide-react';

export default function Classes() {
  const [classes, setClasses] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [formData, setFormData] = useState({
    class_name: '',
    course_code: '',
    department: '',
    batch: '',
    semester: '',
    instructor: ''
  });
  const [error, setError] = useState(null);

  const fetchClasses = async () => {
    try {
      setIsLoading(true);
      const res = await fetch('http://localhost:8000/api/classes');
      const data = await res.json();
      setClasses(data.classes || {});
    } catch (err) {
      console.error(err);
      setError("Failed to fetch classes from server.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchClasses();
  }, []);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleCreateClass = async (e) => {
    e.preventDefault();
    setError(null);
    
    if (!formData.class_name || !formData.course_code || !formData.department || !formData.batch) {
      setError("Please fill out all required fields.");
      return;
    }
    
    try {
      const res = await fetch('http://localhost:8000/api/classes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        setError(data.detail || "Failed to create class");
        return;
      }
      
      // Reset form
      setFormData({
        class_name: '',
        course_code: '',
        department: '',
        batch: '',
        semester: '',
        instructor: ''
      });
      
      // Refresh list
      fetchClasses();
      
    } catch (err) {
      console.error(err);
      setError("Error connecting to server.");
    }
  };

  return (
    <div className="max-w-6xl mx-auto py-6 animation-fade-in space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">Classes</h1>
        <p className="text-slate-500 text-sm mt-1">Manage classes, assign instructors, and set up courses for attendance tracking.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Create Class Form */}
        <div className="lg:col-span-1">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm overflow-hidden">
            <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 flex items-center gap-2">
              <Plus className="w-5 h-5 text-primary" />
              <h2 className="font-semibold text-slate-800 dark:text-slate-100">Create New Class</h2>
            </div>
            
            <form onSubmit={handleCreateClass} className="p-5 space-y-4">
              {error && (
                <div className="p-3 bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400 text-sm rounded border border-red-200 dark:border-red-800/30">
                  {error}
                </div>
              )}
              
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Class Name <span className="text-red-500">*</span></label>
                  <input 
                    type="text" name="class_name" 
                    placeholder="e.g. Intro to Computer Science"
                    value={formData.class_name} onChange={handleInputChange}
                    className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-300 rounded focus:ring-2 focus:ring-primary outline-none dark:bg-slate-800 dark:border-slate-700 dark:text-white"
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Course Code <span className="text-red-500">*</span></label>
                    <input 
                      type="text" name="course_code" 
                      placeholder="e.g. CS101"
                      value={formData.course_code} onChange={handleInputChange}
                      className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-300 rounded focus:ring-2 focus:ring-primary outline-none dark:bg-slate-800 dark:border-slate-700 dark:text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Batch <span className="text-red-500">*</span></label>
                    <input 
                      type="text" name="batch" 
                      placeholder="e.g. 2026"
                      value={formData.batch} onChange={handleInputChange}
                      className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-300 rounded focus:ring-2 focus:ring-primary outline-none dark:bg-slate-800 dark:border-slate-700 dark:text-white"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Department <span className="text-red-500">*</span></label>
                  <input 
                    type="text" name="department" 
                    placeholder="e.g. Computer Science"
                    value={formData.department} onChange={handleInputChange}
                    className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-300 rounded focus:ring-2 focus:ring-primary outline-none dark:bg-slate-800 dark:border-slate-700 dark:text-white"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Semester</label>
                    <input 
                      type="text" name="semester" 
                      placeholder="e.g. Fall"
                      value={formData.semester} onChange={handleInputChange}
                      className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-300 rounded focus:ring-2 focus:ring-primary outline-none dark:bg-slate-800 dark:border-slate-700 dark:text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Instructor</label>
                    <input 
                      type="text" name="instructor" 
                      placeholder="e.g. Dr. Smith"
                      value={formData.instructor} onChange={handleInputChange}
                      className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-300 rounded focus:ring-2 focus:ring-primary outline-none dark:bg-slate-800 dark:border-slate-700 dark:text-white"
                    />
                  </div>
                </div>
              </div>

              <button 
                type="submit" 
                className="w-full mt-4 bg-primary hover:bg-primary-hover text-white py-2 rounded font-medium text-sm transition-colors shadow-sm"
              >
                Create Class
              </button>
            </form>
          </div>
        </div>

        {/* Classes List */}
        <div className="lg:col-span-2">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm overflow-hidden h-full flex flex-col">
            <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2 relative flex-1">
                <Search className="w-4 h-4 text-slate-400 absolute left-3" />
                <input 
                  type="text" 
                  placeholder="Search classes..." 
                  className="w-full pl-9 pr-3 py-2 text-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg outline-none focus:ring-2 focus:ring-primary/50 text-slate-700 dark:text-slate-200"
                />
              </div>
            </div>
            
            <div className="p-0 flex-1 overflow-auto max-h-[600px]">
              {isLoading ? (
                <div className="flex items-center justify-center h-48 text-slate-400">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                </div>
              ) : Object.keys(classes).length === 0 ? (
                <div className="flex flex-col items-center justify-center p-12 text-slate-500">
                  <BookOpen className="w-12 h-12 text-slate-300 mb-4" />
                  <p className="text-base font-medium text-slate-600 dark:text-slate-400">No classes found</p>
                  <p className="text-sm mt-1">Create your first class using the form.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4">
                  {Object.entries(classes).map(([id, cls]) => (
                    <div key={id} className="group border border-slate-200 dark:border-slate-800 rounded-xl p-4 hover:border-primary/50 dark:hover:border-primary/50 hover:shadow-md transition-all bg-white dark:bg-slate-900/50">
                      <div className="flex justify-between items-start mb-3">
                        <div>
                          <h3 className="font-semibold text-slate-900 dark:text-white line-clamp-1 truncate" title={cls.class_name}>
                            {cls.class_name}
                          </h3>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400">
                              {cls.course_code}
                            </span>
                            <span className="text-xs text-slate-500">ID: {id}</span>
                          </div>
                        </div>
                      </div>
                      
                      <div className="space-y-2 mt-4 text-sm">
                        <div className="flex items-center text-slate-600 dark:text-slate-400">
                          <BookMarked className="w-4 h-4 mr-2 text-slate-400" />
                          <span className="truncate">{cls.department}</span>
                        </div>
                        <div className="flex items-center text-slate-600 dark:text-slate-400">
                          <Hash className="w-4 h-4 mr-2 text-slate-400" />
                          <span>Batch {cls.batch} {cls.semester && `· ${cls.semester}`}</span>
                        </div>
                        <div className="flex items-center text-slate-600 dark:text-slate-400">
                          <Users className="w-4 h-4 mr-2 text-slate-400" />
                          <span className="truncate">{cls.instructor || 'Unassigned'}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
        
      </div>
    </div>
  );
}
