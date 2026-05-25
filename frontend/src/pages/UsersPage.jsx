import React, { useState, useEffect } from 'react';
import { adminAPI } from '../services/api';
import { Users, Shield, RefreshCw, AlertCircle, Calendar, User } from 'lucide-react';

export default function UsersPage() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminAPI.getUsers();
      setUsers(data);
    } catch (err) {
      console.error(err);
      setError('Failed to load system user database.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  return (
    <div className="space-y-8 bg-white">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0 pb-6 border-b border-slate-100">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center space-x-2.5">
            <Users className="h-6 w-6 text-indigo-600" />
            <span>Registered Users</span>
          </h1>
          <p className="text-slate-500 text-sm mt-1">Manage system accounts and access credentials</p>
        </div>
        <button
          onClick={fetchUsers}
          className="flex items-center space-x-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 px-4 py-2.5 rounded-lg transition-colors font-medium text-sm"
        >
          <RefreshCw className="h-4 w-4 text-slate-500" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Users Card Container */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        {error && (
          <div className="p-4 bg-red-50 border-b border-red-100 text-red-700 text-sm flex items-center space-x-2">
            <AlertCircle className="h-5 w-5" />
            <span>{error}</span>
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[#F8FAFC] text-xs font-bold text-slate-500 uppercase tracking-wider border-b border-slate-200">
                <th className="py-4 px-6">User Details</th>
                <th className="py-4 px-6">User ID (UUID)</th>
                <th className="py-4 px-6">System Role</th>
                <th className="py-4 px-6">Registration Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm text-slate-700">
              {users.length > 0 ? (
                users.map((item, index) => (
                  <tr key={item.id} className={`hover:bg-[#F8FAFC] transition-colors ${index % 2 === 0 ? 'bg-white' : 'bg-[#F8FAFC]/30'}`}>
                    
                    {/* User Profile Card */}
                    <td className="py-4 px-6">
                      <div className="flex items-center space-x-3">
                        <div className="bg-slate-50 p-2.5 rounded-full text-slate-500 border border-slate-200">
                          <User className="h-4 w-4" />
                        </div>
                        <div>
                          <div className="font-semibold text-slate-900">{item.full_name || 'Anonymous User'}</div>
                          <div className="text-xs text-slate-400">{item.email}</div>
                        </div>
                      </div>
                    </td>

                    {/* User ID */}
                    <td className="py-4 px-6 font-mono text-xs text-slate-400 select-all">
                      {item.id}
                    </td>

                    {/* Role Badge */}
                    <td className="py-4 px-6">
                      <span className={`inline-flex items-center space-x-1.5 text-xs font-semibold px-2.5 py-0.5 rounded-full border ${
                        item.role === 'admin'
                          ? 'bg-indigo-50 border-indigo-200 text-indigo-700'
                          : 'bg-slate-50 border-slate-200 text-slate-600'
                      }`}>
                        {item.role === 'admin' && <Shield className="h-3 w-3" />}
                        <span className="capitalize">{item.role}</span>
                      </span>
                    </td>

                    {/* Created At */}
                    <td className="py-4 px-6 text-xs text-slate-500">
                      <div className="flex items-center space-x-1.5">
                        <Calendar className="h-3.5 w-3.5 text-slate-400" />
                        <span>{new Date(item.created_at).toLocaleString()}</span>
                      </div>
                    </td>

                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="4" className="py-8 text-center text-slate-400 text-sm">
                    {loading ? 'Retrieving user database...' : 'No users found.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
