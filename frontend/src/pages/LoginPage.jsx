import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { authAPI } from '../services/api';
import { Lock, Mail, ShieldAlert, Loader2, User } from 'lucide-react';

export default function LoginPage() {
  const { login, error: authError, loading: authLoading } = useAuth();
  const [isSignup, setIsSignup] = useState(false);
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    if (isSignup) {
      if (!fullName.trim() || !email || !password) {
        setError('Please fill in all fields.');
        setLoading(false);
        return;
      }
      try {
        const full_name = fullName;
        await authAPI.signup(email, password, full_name);
        const success = await login(email, password);
        if (!success) {
          setError('Signup successful, but login failed. Please sign in manually.');
        }
      } catch (err) {
        console.error(err);
        const message = err.response?.data?.detail?.[0]?.msg
          || err.response?.data?.detail
          || 'Something went wrong';
        setError(typeof message === 'string' ? message : JSON.stringify(message));
      }
    } else {
      if (!email || !password) {
        setError('Please enter both email and password.');
        setLoading(false);
        return;
      }
      await login(email, password);
    }
    setLoading(false);
  };

  const toggleMode = () => {
    setIsSignup(prev => !prev);
    setFullName('');
    setEmail('');
    setPassword('');
    setError('');
  };

  const isBtnLoading = loading || authLoading;
  const errorMessage = error || authError;

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F8F9FA] px-4">
      <div className="w-full max-w-md bg-white border border-[#E0E0E0] rounded-xl p-8 shadow-[0_4px_24px_rgba(0,0,0,0.08)]">
        
        {/* Logo and Headings */}
        <div className="flex flex-col items-center mb-8">
          <div className="p-3 border border-[#E0E0E0] rounded-full mb-3 text-black">
            <Lock className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-bold text-black">
            {isSignup ? 'Create an Account' : 'Welcome Back'}
          </h1>
          <p className="text-neutral-500 text-sm mt-1 text-center">
            {isSignup 
              ? 'Get started with Codexial AI Support' 
              : 'Authenticate to access your workspace'}
          </p>
        </div>

        {/* Error Message */}
        {errorMessage && (
          <div className="mb-6 text-red-600 text-sm flex items-start space-x-2">
            <ShieldAlert className="h-5 w-5 shrink-0 mt-0.5 text-red-600" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          {isSignup && (
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-2">
                Full Name
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-neutral-400" />
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full bg-white border border-[#E0E0E0] text-black rounded-lg py-2.5 pl-10 pr-4 placeholder-gray-400 focus:outline-none focus:border-black transition-all text-sm"
                  placeholder="John Doe"
                  required
                  disabled={isBtnLoading}
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-2">
              Email Address
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-neutral-400" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-white border border-[#E0E0E0] text-black rounded-lg py-2.5 pl-10 pr-4 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-black focus:border-black transition-all text-sm"
                placeholder="user@codexial.com"
                required
                disabled={isBtnLoading}
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-2">
              Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-neutral-400" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-white border border-[#E0E0E0] text-black rounded-lg py-2.5 pl-10 pr-4 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-black focus:border-black transition-all text-sm"
                placeholder="••••••••"
                required
                disabled={isBtnLoading}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isBtnLoading}
            className="w-full bg-black hover:bg-neutral-800 text-white font-semibold py-3 px-4 rounded-lg transition-colors shadow-sm flex items-center justify-center space-x-2 disabled:opacity-50"
          >
            {isBtnLoading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>{isSignup ? 'Signing up...' : 'Signing in...'}</span>
              </>
            ) : (
              <span>{isSignup ? 'Sign Up' : 'Sign In'}</span>
            )}
          </button>
        </form>

        {/* Toggle Mode */}
        <div className="mt-6 text-center">
          <button 
            onClick={toggleMode}
            disabled={isBtnLoading}
            className="text-xs text-neutral-600 hover:text-black focus:outline-none"
          >
            {isSignup ? (
              <span>Already have an account? <strong className="text-black hover:underline">Sign In</strong></span>
            ) : (
              <span>Don't have an account? <strong className="text-black hover:underline">Sign Up</strong></span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
