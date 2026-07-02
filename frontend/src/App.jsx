import { Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Overview from "./pages/Overview";
import Players from "./pages/Players";
import MatchHistory from "./pages/MatchHistory";
import MetaShifts from "./pages/MetaShifts";
import WinPrediction from "./pages/WinPrediction";

export default function App() {
  return (
    <div className="flex min-h-screen bg-bg">
      <Sidebar />
      <main className="flex-1 px-8 py-8 max-w-[1400px]">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/players" element={<Players />} />
          <Route path="/matches" element={<MatchHistory />} />
          <Route path="/meta-shifts" element={<MetaShifts />} />
          <Route path="/win-prediction" element={<WinPrediction />} />
        </Routes>
      </main>
    </div>
  );
}