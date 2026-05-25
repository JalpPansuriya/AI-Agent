import React, { useState, useEffect } from 'react';
import { adminAPI } from '../services/api';
import {
  Users,
  MessageSquare,
  Cpu,
  DollarSign,
  Activity,
  AlertTriangle,
  Loader2,
  TrendingUp,
  RefreshCw
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [tokenStats, setTokenStats] = useState(null);
  const [userStats, setUserStats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [platformData, tokenData, usersData] = await Promise.all([
        adminAPI.getPlatformStats(),
        adminAPI.getTokenStats(),
        adminAPI.getUserStats()
      ]);
      setStats(platformData);
      setTokenStats(tokenData);
      setUserStats(usersData);
    } catch (err) {
      console.error(err);
      setError('Failed to fetch analytics dashboard data. Make sure the API server is running.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center space-y-4 bg-white">
        <Loader2 className="h-8 w-8 text-indigo-600 animate-spin" />
        <p className="text-slate-500 text-sm">Aggregating platform metrics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center space-y-4 px-4 text-center bg-white">
        <div className="bg-red-50 p-4 rounded-full border border-red-100 text-red-500">
          <AlertTriangle className="h-8 w-8" />
        </div>
        <h2 className="text-lg font-bold text-slate-900">Error Loading Dashboard</h2>
        <p className="text-slate-500 text-sm max-w-md">{error}</p>
        <button
          onClick={fetchData}
          className="mt-2 flex items-center space-x-2 bg-slate-100 border border-slate-200 text-slate-700 px-4 py-2 rounded-lg hover:bg-slate-200 transition"
        >
          <RefreshCw className="h-4 w-4" />
          <span>Retry</span>
        </button>
      </div>
    );
  }

  // Prepping data for chart: User token distributions
  const chartData = userStats
    .slice()
    .sort((a, b) => b.token_count - a.token_count)
    .slice(0, 5)
    .map(u => ({
      name: u.full_name || u.email.split('@')[0],
      tokens: u.token_count,
      messages: u.message_count,
    }));

  return (
    <div className="space-y-8 bg-white">
      
      {/* Header Panel */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0 pb-6 border-b border-slate-100">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Platform Analytics</h1>
          <p className="text-slate-500 text-sm mt-1">Real-time usage and consumption metrics</p>
        </div>
        <button
          onClick={fetchData}
          className="flex items-center space-x-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 px-4 py-2.5 rounded-lg transition-colors font-medium text-sm"
        >
          <RefreshCw className="h-4 w-4 text-slate-500" />
          <span>Refresh Data</span>
        </button>
      </div>

      {/* Grid Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        
        {/* Total Users */}
        <div className="bg-white border border-slate-200 border-t-4 border-t-indigo-500 rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-sm font-semibold text-slate-500 uppercase tracking-wide block">Total Users</span>
              <span className="text-3xl font-extrabold text-slate-900 block mt-2">{stats?.total_users}</span>
            </div>
            <div className="bg-indigo-50 p-3 rounded-lg border border-indigo-100 text-indigo-600">
              <Users className="h-5 w-5" />
            </div>
          </div>
          <div className="text-xs text-slate-500 mt-4 flex items-center space-x-1.5">
            <TrendingUp className="h-3.5 w-3.5 text-indigo-500" />
            <span>Total registered user database</span>
          </div>
        </div>

        {/* Active Sessions */}
        <div className="bg-white border border-slate-200 border-t-4 border-t-cyan-500 rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-sm font-semibold text-slate-500 uppercase tracking-wide block">Active Sessions</span>
              <span className="text-3xl font-extrabold text-slate-900 block mt-2">{stats?.active_sessions_today}</span>
            </div>
            <div className="bg-cyan-50 p-3 rounded-lg border border-cyan-100 text-cyan-600">
              <MessageSquare className="h-5 w-5" />
            </div>
          </div>
          <div className="text-xs text-slate-500 mt-4 flex items-center space-x-1.5">
            <Activity className="h-3.5 w-3.5 text-cyan-500" />
            <span>Unique active chats today</span>
          </div>
        </div>

        {/* Token Traffic */}
        <div className="bg-white border border-slate-200 border-t-4 border-t-emerald-500 rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-sm font-semibold text-slate-500 uppercase tracking-wide block">Today's Tokens</span>
              <span className="text-3xl font-extrabold text-slate-900 block mt-2">{stats?.total_tokens_today?.toLocaleString() || 0}</span>
            </div>
            <div className="bg-emerald-50 p-3 rounded-lg border border-emerald-100 text-emerald-600">
              <Cpu className="h-5 w-5" />
            </div>
          </div>
          <div className="text-xs text-slate-500 mt-4 flex items-center space-x-1.5">
            <span className="text-slate-400 font-medium">Daily Cost:</span>
            <span className="font-semibold text-emerald-600">${stats?.estimated_cost_today_usd?.toFixed(6) || 0}</span>
          </div>
        </div>

        {/* Avg Response Time */}
        <div className="bg-white border border-slate-200 border-t-4 border-t-amber-500 rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-sm font-semibold text-slate-500 uppercase tracking-wide block">Response Time</span>
              <span className="text-3xl font-extrabold text-slate-900 block mt-2">{stats?.avg_response_time_ms?.toFixed(1) || 0} ms</span>
            </div>
            <div className="bg-amber-50 p-3 rounded-lg border border-amber-100 text-amber-600">
              <Activity className="h-5 w-5" />
            </div>
          </div>
          <div className="text-xs text-slate-500 mt-4 flex items-center space-x-1.5">
            <span className="text-slate-400 font-medium">Err Rate:</span>
            <span className={`font-semibold ${stats?.error_rate_percent > 5 ? 'text-red-500' : 'text-emerald-600'}`}>
              {stats?.error_rate_percent?.toFixed(2)}%
            </span>
          </div>
        </div>

      </div>

      {/* Cumulative Stats and Graphs */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Cumulative Stats Card */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col justify-between">
          <div>
            <h3 className="text-lg font-bold text-slate-900 mb-1">Cumulative Usage</h3>
            <p className="text-slate-400 text-xs mb-6">Historical aggregation of platform-wide tokens</p>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <span className="text-sm text-slate-500">Prompt Tokens</span>
                <span className="text-sm font-semibold text-slate-800">{tokenStats?.prompt_tokens?.toLocaleString() || 0}</span>
              </div>
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <span className="text-sm text-slate-500">Completion Tokens</span>
                <span className="text-sm font-semibold text-slate-800">{tokenStats?.completion_tokens?.toLocaleString() || 0}</span>
              </div>
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <span className="text-sm text-slate-500">Total Tokens</span>
                <span className="text-sm font-semibold text-slate-800">{tokenStats?.total_tokens?.toLocaleString() || 0}</span>
              </div>
            </div>
          </div>

          <div className="mt-8 bg-slate-50 border border-slate-200 p-4 rounded-lg flex items-center space-x-3">
            <div className="bg-emerald-50 p-2.5 rounded-lg border border-emerald-100 text-emerald-600">
              <DollarSign className="h-5 w-5" />
            </div>
            <div>
              <span className="text-xs text-slate-400 block uppercase tracking-wider font-semibold">Cumulative Cost</span>
              <span className="text-xl font-bold text-emerald-600">${tokenStats?.estimated_cost_usd?.toFixed(6) || 0}</span>
            </div>
          </div>
        </div>

        {/* User Token Usage Chart */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 lg:col-span-2 shadow-sm">
          <h3 className="text-lg font-bold text-slate-900 mb-1">Top Users Token Usage</h3>
          <p className="text-slate-400 text-xs mb-6">Comparison of total token traffic and messages per active client</p>

          <div className="h-64">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
                  <YAxis yAxisId="left" stroke="#6366F1" fontSize={11} tickLine={false} />
                  <YAxis yAxisId="right" orientation="right" stroke="#06B6D4" fontSize={11} tickLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e2e8f0', color: '#0f172a' }}
                    labelStyle={{ fontWeight: 'bold', color: '#6366F1' }}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px', color: '#64748b' }} />
                  <Line yAxisId="left" type="monotone" dataKey="tokens" name="Total Tokens" stroke="#6366F1" activeDot={{ r: 6 }} strokeWidth={2} />
                  <Line yAxisId="right" type="monotone" dataKey="messages" name="Message Count" stroke="#06B6D4" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-400 text-sm">
                No active traffic logs to show user distributions.
              </div>
            )}
          </div>
        </div>

      </div>

    </div>
  );
}
