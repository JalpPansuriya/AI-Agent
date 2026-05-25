import React, { useState, useEffect } from 'react';
import { adminAPI } from '../services/api';
import { FileText, Search, RefreshCw, AlertCircle, Filter, Calendar } from 'lucide-react';

export default function LogsPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filter states
  const [endpoint, setEndpoint] = useState('');
  const [statusCode, setStatusCode] = useState('');
  const [userId, setUserId] = useState('');
  const [limit, setLimit] = useState('100');

  const fetchLogs = async (e) => {
    if (e) e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const filters = {};
      if (endpoint.trim()) filters.endpoint = endpoint.trim();
      if (statusCode.trim()) filters.status_code = parseInt(statusCode.trim(), 10);
      if (userId.trim()) filters.user_id = userId.trim();
      filters.limit = parseInt(limit, 10) || 100;

      const data = await adminAPI.getLogs(filters);
      setLogs(data);
    } catch (err) {
      console.error(err);
      setError('Failed to fetch request audit logs.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const handleReset = () => {
    setEndpoint('');
    setStatusCode('');
    setUserId('');
    setLimit('100');
    setTimeout(() => {
      adminAPI.getLogs({ limit: 100 }).then(setLogs).catch(console.error);
    }, 0);
  };

  const getStatusBadgeClass = (status) => {
    if (status >= 500) return 'bg-red-50 border border-red-200 text-red-700';
    if (status >= 400) return 'bg-amber-50 border border-amber-200 text-amber-700';
    if (status >= 300) return 'bg-blue-50 border border-blue-200 text-blue-700';
    return 'bg-emerald-50 border border-emerald-200 text-emerald-700';
  };

  return (
    <div className="space-y-8 bg-white">
      
      {/* Header */}
      <div className="pb-6 border-b border-slate-100">
        <h1 className="text-2xl font-bold text-slate-900 flex items-center space-x-2.5">
          <FileText className="h-6 w-6 text-indigo-600" />
          <span>System Request Logs</span>
        </h1>
        <p className="text-slate-500 text-sm mt-1">Audit log of system requests, durations, and response codes</p>
      </div>

      {/* Filters Form */}
      <form onSubmit={fetchLogs} className="bg-[#F8FAFC] border border-slate-200 rounded-xl p-6 space-y-4">
        <div className="flex items-center space-x-2 border-b border-slate-200 pb-3 mb-2">
          <Filter className="h-4 w-4 text-indigo-600" />
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">Filter Logs</span>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          
          {/* Endpoint Filter */}
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Endpoint</label>
            <input
              type="text"
              value={endpoint}
              onChange={(e) => setEndpoint(e.target.value)}
              placeholder="e.g. /api/v1/chat"
              className="w-full bg-white border border-slate-200 rounded-lg py-2 px-3 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
            />
          </div>

          {/* Status Code Filter */}
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Status Code</label>
            <input
              type="number"
              value={statusCode}
              onChange={(e) => setStatusCode(e.target.value)}
              placeholder="e.g. 200"
              className="w-full bg-white border border-slate-200 rounded-lg py-2 px-3 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
            />
          </div>

          {/* User ID Filter */}
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">User ID (UUID)</label>
            <input
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="e.g. 550e8400-e29b-..."
              className="w-full bg-white border border-slate-200 rounded-lg py-2 px-3 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
            />
          </div>

          {/* Limit Filter */}
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Max Logs</label>
            <select
              value={limit}
              onChange={(e) => setLimit(e.target.value)}
              className="w-full bg-white border border-slate-200 rounded-lg py-2 px-3 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
            >
              <option value="50">50 rows</option>
              <option value="100">100 rows</option>
              <option value="200">200 rows</option>
              <option value="500">500 rows</option>
            </select>
          </div>

        </div>

        <div className="flex justify-end space-x-3 pt-2">
          <button
            type="button"
            onClick={handleReset}
            className="bg-white border border-slate-200 text-slate-600 py-2 px-4 rounded-lg hover:bg-slate-50 transition text-sm font-semibold shadow-sm"
          >
            Reset
          </button>
          <button
            type="submit"
            disabled={loading}
            className="bg-indigo-600 text-white py-2 px-6 rounded-lg hover:bg-indigo-500 transition text-sm font-semibold flex items-center space-x-2 shadow-sm"
          >
            {loading ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <Search className="h-4 w-4" />
            )}
            <span>Apply Filters</span>
          </button>
        </div>
      </form>

      {/* Logs Table Results */}
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
                <th className="py-4 px-6">Timestamp</th>
                <th className="py-4 px-6">Request ID</th>
                <th className="py-4 px-6">Method</th>
                <th className="py-4 px-6">Endpoint</th>
                <th className="py-4 px-6 text-center">Status</th>
                <th className="py-4 px-6 text-right">Duration</th>
                <th className="py-4 px-6 text-right">Tokens</th>
                <th className="py-4 px-6">Error Detail</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm text-slate-700">
              {logs.length > 0 ? (
                logs.map((log, index) => (
                  <tr key={log.id} className={`hover:bg-[#F8FAFC] transition-colors ${index % 2 === 0 ? 'bg-white' : 'bg-[#F8FAFC]/30'}`}>
                    
                    {/* Timestamp */}
                    <td className="py-3 px-6 whitespace-nowrap text-xs text-slate-500">
                      <div className="flex items-center space-x-1.5">
                        <Calendar className="h-3.5 w-3.5 text-slate-400" />
                        <span>{new Date(log.created_at).toLocaleString()}</span>
                      </div>
                    </td>
                    
                    {/* Request ID */}
                    <td className="py-3 px-6 font-mono text-xs text-slate-400 select-all" title={log.request_id}>
                      {log.request_id ? `${log.request_id.slice(0, 8)}...` : 'N/A'}
                    </td>
                    
                    {/* Method */}
                    <td className="py-3 px-6">
                      <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                        log.method === 'POST' ? 'text-indigo-700 bg-indigo-50 border border-indigo-100' :
                        log.method === 'GET' ? 'text-cyan-700 bg-cyan-50 border border-cyan-100' : 'text-slate-600 bg-slate-50 border border-slate-150'
                      }`}>
                        {log.method}
                      </span>
                    </td>
                    
                    {/* Endpoint */}
                    <td className="py-3 px-6 font-mono text-xs text-slate-700">
                      {log.endpoint}
                    </td>
                    
                    {/* Status Code (pill badges with border and background) */}
                    <td className="py-3 px-6 text-center">
                      <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${getStatusBadgeClass(log.status_code)}`}>
                        {log.status_code}
                      </span>
                    </td>
                    
                    {/* Duration */}
                    <td className="py-3 px-6 text-right font-mono text-xs text-slate-500">
                      {log.duration_ms ? `${log.duration_ms}ms` : '0ms'}
                    </td>
                    
                    {/* Tokens */}
                    <td className="py-3 px-6 text-right font-mono text-xs text-indigo-600">
                      {log.tokens_used ? log.tokens_used.toLocaleString() : 0}
                    </td>
                    
                    {/* Error Message */}
                    <td className="py-3 px-6 text-xs text-red-600 font-mono truncate max-w-xs" title={log.error_message}>
                      {log.error_message || <span className="text-slate-400">-</span>}
                    </td>

                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="8" className="py-8 text-center text-slate-400 text-sm">
                    {loading ? 'Retrieving audit logs...' : 'No system request logs match your filter criteria.'}
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
