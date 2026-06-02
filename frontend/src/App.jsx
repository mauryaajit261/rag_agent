import { useState, useEffect } from 'react';
import './App.css';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import DocumentManager from './components/DocumentManager';
import DatabaseManager from './components/DatabaseManager';
import api from './api';
import { supabase } from './supabaseClient';
import Auth from './components/Auth';
import ProfileManager from './components/ProfileManager';

function App() {
  const [activeView, setActiveView] = useState('chat');
  const [systemHealth, setSystemHealth] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [messages, setMessages] = useState([]);
  const [sourceType, setSourceType] = useState('all');
  const [session, setSession] = useState(null);
  const [chatRefreshKey, setChatRefreshKey] = useState(0);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
    });

    supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });

    checkSystemHealth();
    const interval = setInterval(checkSystemHealth, 30000); // Check every 30s
    return () => clearInterval(interval);
  }, []);

  // Auto-collapse the main nav on narrow screens so the content area gets the space.
  // Only force-collapses when narrow — on wide screens the header ☰ keeps manual control.
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 1024) setIsSidebarOpen(false);
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const checkSystemHealth = async () => {
    try {
      const health = await api.healthCheck();
      setSystemHealth(health);
    } catch (error) {
      console.error('Health check failed:', error);
      // Surface the error detail for better debugging
      setSystemHealth({
        status: 'unhealthy',
        error: error.message,
        detail: `Could not connect to backend at ${api.baseURL}. ${error.message}`
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p className="loading-text">Initializing mySetu AI...</p>
      </div>
    );
  }

  // Auth Gate
  if (!session) {
    return <Auth />;
  }

  return (
    <div className="app">
      <Header systemHealth={systemHealth} session={session} />

      <div className="app-body">
        <Sidebar activeView={activeView} onViewChange={setActiveView} isOpen={isSidebarOpen} />

        {/* Collapse handle on the sidebar's right edge — stays visible when collapsed */}
        <button
          className={`sidebar-collapse-toggle ${isSidebarOpen ? '' : 'collapsed'}`}
          onClick={() => setIsSidebarOpen(v => !v)}
          title={isSidebarOpen ? 'Collapse menu' : 'Expand menu'}
          aria-label="Toggle navigation menu"
        >
          {isSidebarOpen ? '⟨' : '⟩'}
        </button>

        <main className="main-content">
          {/* All views always mounted — tab switches never interrupt in-flight operations */}
          <div style={{ display: activeView === 'chat' ? 'contents' : 'none' }}>
            <ChatInterface
              key={chatRefreshKey}
              systemHealth={systemHealth}
              messages={messages}
              setMessages={setMessages}
              sourceType={sourceType}
              setSourceType={setSourceType}
              checkSystemHealth={checkSystemHealth}
            />
          </div>
          <div style={{ display: activeView === 'documents' ? 'contents' : 'none' }}>
            <DocumentManager onRefresh={checkSystemHealth} />
          </div>
          <div style={{ display: activeView === 'databases' ? 'contents' : 'none' }}>
            <DatabaseManager onRefresh={checkSystemHealth} />
          </div>
          <div style={{ display: activeView === 'profile' ? 'contents' : 'none' }}>
            <ProfileManager session={session} />
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
