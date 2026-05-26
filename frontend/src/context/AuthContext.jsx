import React, { createContext, useContext, useState } from 'react';
import { authAPI, setAuthToken } from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(() => {
    const savedToken = localStorage.getItem('token');
    if (savedToken) {
      setAuthToken(savedToken);
    }
    return savedToken;
  });
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('user');
    try {
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const login = async (email, password) => {
    setLoading(true);
    setError(null);
    try {
      // 1. Authenticate credentials
      const tokenData = await authAPI.login(email, password);
      const accessToken = tokenData.access_token;
      
      // 2. Set token in-memory and update Axios header
      setToken(accessToken);
      setAuthToken(accessToken);
      localStorage.setItem('token', accessToken);
      localStorage.setItem('refresh_token', tokenData.refresh_token);

      // 3. Fetch user profile
      const userProfile = await authAPI.me();
      
      setUser(userProfile);
      localStorage.setItem('user', JSON.stringify(userProfile));
      setLoading(false);
      return true;
    } catch (err) {
      setToken(null);
      setAuthToken(null);
      setUser(null);
      localStorage.removeItem('token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      const message = err.response?.data?.detail || 'Invalid email or password';
      setError(message);
      setLoading(false);
      return false;
    }
  };

  const logout = () => {
    setToken(null);
    setAuthToken(null);
    setUser(null);
    setError(null);
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  };

  React.useEffect(() => {
    window.__authLogout = logout;
    return () => { delete window.__authLogout; };
  }, [logout]);

  const getToken = () => token;

  return (
    <AuthContext.Provider
      value={{
        token,
        getToken,
        user,
        loading,
        error,
        login,
        logout,
        isAuthenticated: !!token,
        isAdmin: user?.role === 'admin',
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
