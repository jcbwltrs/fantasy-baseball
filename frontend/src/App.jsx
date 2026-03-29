import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import WaiverWire from './pages/WaiverWire';
import MyRoster from './pages/MyRoster';
import LineupOptimizer from './pages/LineupOptimizer';
import Matchup from './pages/Matchup';
import Guide from './pages/Guide';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000, // 1 minute
      retry: 2,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-[#F7F1D1]">
          <Navbar />
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/waiver-wire" element={<WaiverWire />} />
            <Route path="/roster" element={<MyRoster />} />
            <Route path="/lineup" element={<LineupOptimizer />} />
            <Route path="/matchup" element={<Matchup />} />
            <Route path="/guide" element={<Guide />} />
          </Routes>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
