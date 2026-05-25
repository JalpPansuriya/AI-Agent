import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import LogsPage from './pages/LogsPage';
import UsersPage from './pages/UsersPage';
import ChatPage from './pages/ChatPage';

function AppContent() {
  const { isAuthenticated, logout, user, isAdmin } = useAuth();
  const [currentPage, setCurrentPage] = useState('dashboard');

  if (!isAuthenticated) return <LoginPage />;

  if (!isAdmin) return <ChatPage />;

  return (
    <div className="min-h-screen bg-white flex">
      <Navbar currentPage={currentPage} setCurrentPage={setCurrentPage} onLogout={logout} user={user} />
      <div className="flex-1 bg-white min-h-screen overflow-y-auto">
        <main className="p-8">
          {currentPage === 'dashboard' && <DashboardPage />}
          {currentPage === 'logs' && <LogsPage />}
          {currentPage === 'users' && <UsersPage />}
          {currentPage === 'chat' && <ChatPage />}
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return <AuthProvider><AppContent /></AuthProvider>;
}
