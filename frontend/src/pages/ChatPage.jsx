  import React, { useState, useEffect, useRef } from 'react';
  import { chatAPI } from '../services/api';
  import { useAuth } from '../context/AuthContext';
  import { PromptInputBox } from '../components/ui/ai-prompt-box';
  import ReactMarkdown from 'react-markdown';

  export default function ChatPage() {
    const { user, logout } = useAuth();
    const [sessions, setSessions] = useState([]);
    const [activeSession, setActiveSession] = useState(null);
    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(false);
    const [sessionLoading, setSessionLoading] = useState(false);
    const [error, setError] = useState(null);
    const messagesEndRef = useRef(null);
    const hasInitialized = useRef(false);

    const [editingTitle, setEditingTitle] = useState(false);
    const [titleInput, setTitleInput] = useState('');

    const handleTitleClick = () => {
      setTitleInput(activeSession.title || '');
      setEditingTitle(true);
    };

    const handleTitleSave = async () => {
      if (titleInput.trim() && titleInput !== activeSession.title) {
        await chatAPI.updateSession(activeSession.id, titleInput.trim());
        setSessions(prev => prev.map(s =>
          s.id === activeSession.id ? { ...s, title: titleInput.trim() } : s
        ));
        setActiveSession(prev => ({ ...prev, title: titleInput.trim() }));
      }
      setEditingTitle(false);
    };

    useEffect(() => {
      if (hasInitialized.current) return;
      hasInitialized.current = true;
      const initChat = async () => {
        const data = await loadSessions();
        if (data.length === 0) {
          await createSession();
        }
      };
      initChat();
    }, []);

    useEffect(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    useEffect(() => {
      if (activeSession) {
        loadMessages(activeSession.id);
      }
    }, [activeSession]);

    const loadSessions = async () => {
      try {
        const data = await chatAPI.getSessions();
        setSessions(data);
        if (data.length > 0) {
          setActiveSession(data[0]);
        }
        return data;
      } catch (err) {
        console.error(err);
        return [];
      }
    };

    const loadMessages = async (sessionId) => {
      try {
        const data = await chatAPI.getMessages(sessionId);
        const normalized = data.map(m => ({
          id: m.id,
          role: m.role,
          content: m.content || '',
          recommendations: m.recommendations || []
        }));
        setMessages(normalized);
      } catch (err) {
        console.error(err);
      }
    };

    const createSession = async () => {
      setSessionLoading(true);
      try {
        const session = await chatAPI.createSession('New Chat');
        setSessions(prev => [session, ...prev]);
        setActiveSession(session);
        setMessages([]);
      } catch (err) {
        console.error(err);
      }
      setSessionLoading(false);
    };

    const deleteSession = async (sessionId, e) => {
      e.stopPropagation();
      try {
        await chatAPI.deleteSession(sessionId);
        const updated = sessions.filter(s => s.id !== sessionId);
        setSessions(updated);
        if (activeSession?.id === sessionId) {
          setActiveSession(updated[0] || null);
          setMessages([]);
        }
      } catch (err) {
        console.error(err);
      }
    };

    const handleSend = async (content) => {
      if (!content.trim() || !activeSession || loading) return;
      setError(null);
      setLoading(true);

      const token = localStorage.getItem('token');
      const wsBase = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
      const wsUrl = `${wsBase}/api/v1/ws/chat/${activeSession.id}?token=${token}`;
      const ws = new WebSocket(wsUrl);

      // Add user message immediately
      const userMsg = { id: Date.now(), role: 'user', content };
      setMessages(prev => [...prev, userMsg]);

      // Add empty assistant message that will be filled as chunks arrive
      const assistantId = Date.now() + 1;
      setMessages(prev => [...prev, { id: assistantId, role: 'assistant', content: '', recommendations: [] }]);

      let fullContent = '';

      ws.onopen = () => {
        ws.send(JSON.stringify({ content }));
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.error) {
          setError(data.error);
          setLoading(false);
          setMessages(prev => prev.filter(m => m.id !== assistantId));
          ws.close();
          return;
        }

        if (data.chunk) {
          fullContent += data.chunk;
          setMessages(prev => prev.map(m =>
            m.id === assistantId
              ? { ...m, content: fullContent }
              : m
          ));
        }

        if (data.done) {
          setMessages(prev => prev.map(m =>
            m.id === assistantId
              ? { ...m, content: data.full_content || fullContent, recommendations: data.recommendations || [] }
              : m
          ));
          setLoading(false);
          ws.close();

          // Update session title if needed
          if (!activeSession.title || activeSession.title === 'New Chat') {
            const newTitle = content.slice(0, 30) + (content.length > 30 ? '...' : '');
            chatAPI.updateSession(activeSession.id, newTitle).then(() => {
              setSessions(prev => prev.map(s =>
                s.id === activeSession.id ? { ...s, title: newTitle } : s
              ));
              setActiveSession(prev => ({ ...prev, title: newTitle }));
            });
          }
        }
      };

      ws.onerror = () => {
        setError('Connection error. Please try again.');
        setLoading(false);
        setMessages(prev => prev.filter(m => m.id !== assistantId));
      };

      ws.onclose = (event) => {
        if (event.code !== 1000 && event.code !== 1001) {
          setLoading(false);
        }
      };
    };

    return (
      <div className="flex h-screen bg-[#111113]">
        {/* Sidebar */}
        <div className="w-64 bg-[#1A1A1F] border-r border-[#2E2E35] flex flex-col">
          <div className="p-4 border-b border-[#2E2E35]">
            <h1 className="text-white font-semibold text-lg">AI Support</h1>
            <p className="text-gray-400 text-xs mt-1 truncate">{user?.email}</p>
          </div>
          <div className="p-3">
            <button onClick={createSession} disabled={sessionLoading}
              className="w-full py-2 px-3 bg-[#2E2E35] hover:bg-[#3A3A40] text-white text-sm rounded-xl border border-[#444444] transition-colors disabled:opacity-50">
              {sessionLoading ? 'Creating...' : '+ New Chat'}
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {sessions.map(session => (
              <div key={session.id} onClick={() => setActiveSession(session)}
                className={`flex items-center justify-between p-2 rounded-xl cursor-pointer group transition-colors ${
                  activeSession?.id === session.id ? 'bg-[#2E2E35]' : 'hover:bg-[#232328]'
                }`}>
                <span className="text-gray-300 text-sm truncate flex-1">{session.title || 'Untitled'}</span>
                <button onClick={(e) => deleteSession(session.id, e)}
                  className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400 ml-2 text-xs transition-opacity">✕</button>
              </div>
            ))}
            {sessions.length === 0 && <p className="text-gray-600 text-xs text-center mt-4">No chats yet</p>}
          </div>
          <div className="p-3 border-t border-[#2E2E35]">
            <button onClick={logout}
              className="w-full py-2 px-3 text-sm text-gray-500 hover:text-gray-200 hover:bg-[#2E2E35] rounded-xl transition-colors">
              Logout
            </button>
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 flex flex-col">
          {activeSession ? (
            <>
              <div className="bg-[#1A1A1F] border-b border-[#2E2E35] px-6 py-4">
                {editingTitle ? (
                  <input
                    autoFocus
                    value={titleInput}
                    onChange={(e) => setTitleInput(e.target.value)}
                    onBlur={handleTitleSave}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleTitleSave();
                      if (e.key === 'Escape') setEditingTitle(false);
                    }}
                    className="bg-transparent text-white font-medium border-b border-gray-500 outline-none w-full max-w-xs"
                  />
                ) : (
                  <h2
                    onClick={handleTitleClick}
                    className="text-white font-medium cursor-pointer hover:text-gray-300 transition-colors"
                    title="Click to rename"
                  >
                    {activeSession.title || 'Untitled Chat'}
                  </h2>
                )}
              </div>

              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {messages.length === 0 && !loading && (
                  <div className="text-center text-gray-600 mt-20">
                    <p className="text-xl">How can I help you today?</p>
                    <p className="text-sm mt-2">Ask me anything or request product recommendations.</p>
                  </div>
                )}
                {messages.map((msg, idx) => (
                  <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-lg px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                      msg.role === 'user'
                        ? 'bg-[#2E2E35] text-gray-100 rounded-br-sm border border-[#444444]'
                        : 'bg-[#1F2023] text-gray-200 rounded-bl-sm border border-[#333333]'
                    }`}>
                      {msg.role === 'assistant' ? (
                        <div className="prose prose-invert prose-sm max-w-none">
                          <ReactMarkdown>
                            {msg.content}
                          </ReactMarkdown>
                        </div>
                      ) : (
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                      )}
                      {msg.recommendations?.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-[#333333] space-y-2">
                          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Recommendations</p>
                          {msg.recommendations.map((rec, i) => (
                            <div key={i} className="bg-[#2E2E35] rounded-xl p-2 border border-[#444444]">
                              <a
                                href={`https://www.google.com/search?q=${encodeURIComponent(rec.name)}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="font-medium text-blue-400 hover:underline text-xs"
                              >
                                {rec.name}
                              </a>
                              <p className="text-gray-500 text-xs mt-1">{rec.description}</p>
                              {rec.price && <p className="text-blue-400 text-xs font-semibold mt-1">{rec.price}</p>}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {loading && (
                  <div className="flex justify-start">
                    <div className="bg-[#1F2023] border border-[#333333] rounded-2xl rounded-bl-sm px-4 py-3">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{animationDelay:'0ms'}}></div>
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{animationDelay:'150ms'}}></div>
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{animationDelay:'300ms'}}></div>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* PromptInputBox at bottom */}
              <div className="p-4 bg-[#111113] border-t border-[#2E2E35]">
                <div className="max-w-3xl mx-auto">
                  {error && (
                    <div className="mb-3 p-3 bg-red-950/30 border border-red-500/50 text-red-200 text-sm rounded-2xl flex items-center justify-between">
                      <span>{error}</span>
                      <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300 ml-2 font-medium">✕</button>
                    </div>
                  )}
                  <PromptInputBox
                    onSend={handleSend}
                    isLoading={loading}
                    placeholder="Ask me anything..."
                    onInputChange={() => setError(null)}
                  />
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-600">
              <div className="text-center">
                <p className="text-xl mb-2">No chat selected</p>
                <button onClick={createSession} className="text-blue-500 hover:underline text-sm">Start a new chat</button>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }
