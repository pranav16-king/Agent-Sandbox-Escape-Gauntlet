import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from '@/theme/ThemeProvider';
import { TopBar } from '@/components/TopBar';
import { Sidebar } from '@/components/Sidebar';
import { SandboxBanner } from '@/components/SandboxBanner';
import { SandboxModal } from '@/components/SandboxModal';
import { LogDrawer } from '@/features/logs/LogDrawer';
import { useLiveConnection } from '@/api/ws';
import { useLiveStore } from '@/store/liveStore';
import { api } from '@/api/rest';

// Pages
import { Dashboard } from '@/pages/Dashboard';
import { LiveAgent } from '@/pages/LiveAgent';
import { AuditLog } from '@/pages/AuditLog';
import { Scenarios } from '@/pages/Scenarios';
import { Runtime } from '@/pages/Runtime';
import { Policy } from '@/pages/Policy';

const queryClient = new QueryClient();

const AppContent: React.FC = () => {
  // Activate live WebSocket connection
  useLiveConnection();

  const setSnapshot = useLiveStore((s) => s.setSnapshot);
  const connectionStatus = useLiveStore((s) => s.connectionStatus);

  // Load initial snapshot from server
  useEffect(() => {
    let isMounted = true;

    async function loadInitialData() {
      try {
        const snapshot = await api.getSnapshot();
        if (isMounted && snapshot && snapshot.counts) {
          setSnapshot(snapshot);
        }
      } catch (err) {
        console.warn('Backend snapshot not yet available, awaiting live connection:', err);
      }
    }

    loadInitialData();

    return () => {
      isMounted = false;
    };
  }, [setSnapshot]);

  // Fallback polling: if WebSocket is offline, keep dashboard telemetry live every 4s
  useEffect(() => {
    if (connectionStatus !== 'offline') return;

    const interval = setInterval(async () => {
      try {
        const snapshot = await api.getSnapshot();
        if (snapshot && snapshot.counts) {
          setSnapshot(snapshot);
        }
      } catch {}
    }, 4000);

    return () => clearInterval(interval);
  }, [connectionStatus, setSnapshot]);

  return (
    <div className="h-screen max-h-screen overflow-hidden bg-bg text-ink flex flex-col antialiased selection:bg-accent selection:text-on-accent">
      {/* Persistent banner shown on every page when sandbox is OFF */}
      <SandboxBanner />

      {/* Sticky top navigation bar */}
      <TopBar />

      <div className="flex-1 flex min-h-0 overflow-hidden relative">
        {/* Responsive left sidebar */}
        <Sidebar />

        {/* Main scrollable view */}
        <main className="flex-1 min-h-0 overflow-y-auto p-4 lg:p-6 bg-bg transition-colors">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/agent" element={<LiveAgent />} />
            <Route path="/audit" element={<AuditLog />} />
            <Route path="/scenarios" element={<Scenarios />} />
            <Route path="/runtime" element={<Runtime />} />
            <Route path="/policy" element={<Policy />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>

      {/* Global 480px log detail drawer */}
      <LogDrawer />

      {/* Sandbox ON/OFF confirmation dialog */}
      <SandboxModal />
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <BrowserRouter>
          <AppContent />
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
};

export default App;
