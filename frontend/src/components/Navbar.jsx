import React from 'react';
import { LayoutDashboard, FileText, Users, LogOut, Terminal } from 'lucide-react';

export default function Navbar({ currentPage, setCurrentPage, onLogout, user }) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'logs', label: 'Logs', icon: FileText },
    { id: 'users', label: 'Users', icon: Users },
  ];

  return (
    <aside className="w-64 bg-slate-800 border-r border-slate-700/60 flex flex-col h-screen sticky top-0 shrink-0 shadow-lg text-slate-100 z-40">
      
      {/* Sidebar Top: Logo/Title */}
      <div className="p-6 border-b border-slate-700/40 flex items-center space-x-3">
        <div className="bg-indigo-500/10 p-2 rounded-lg border border-indigo-500/30">
          <Terminal className="h-5 w-5 text-indigo-400" />
        </div>
        <div>
          <div className="flex items-center space-x-1.5">
            <span className="font-extrabold text-lg tracking-tight text-white">
              Codexial
            </span>
            <div className="h-2 w-2 rounded-full bg-indigo-500"></div>
          </div>
          <span className="text-xs block text-slate-400 -mt-1 font-semibold uppercase tracking-wider">
            Admin Console
          </span>
        </div>
      </div>

      {/* Sidebar Middle: Navigation Links */}
      <div className="flex-1 px-4 py-6 space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentPage === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setCurrentPage(item.id)}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-150 ${
                isActive
                  ? 'bg-indigo-50 text-indigo-600 border-l-4 border-indigo-600 font-semibold shadow-sm'
                  : 'text-slate-300 hover:text-white hover:bg-slate-700/50 border-l-4 border-transparent'
              }`}
            >
              <Icon className={`h-4 w-4 ${isActive ? 'text-indigo-600' : 'text-slate-400 group-hover:text-white'}`} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

      {/* Sidebar Bottom: User Info & Logout Button */}
      <div className="p-4 border-t border-slate-700/40 bg-slate-900/40 space-y-4">
        {/* User Card */}
        <div className="px-2 py-1.5">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Authenticated As</div>
          <div className="text-sm font-semibold text-slate-200 truncate">{user?.full_name || 'Admin User'}</div>
          <div className="text-xs text-slate-500 truncate">{user?.email}</div>
        </div>

        {/* Logout Button */}
        <button
          onClick={onLogout}
          className="w-full flex items-center space-x-3 px-4 py-2.5 rounded-lg text-sm font-medium text-slate-400 hover:text-white hover:bg-red-600/90 transition-all duration-150 border border-transparent hover:border-red-600"
        >
          <LogOut className="h-4 w-4" />
          <span>Logout</span>
        </button>
      </div>

    </aside>
  );
}
