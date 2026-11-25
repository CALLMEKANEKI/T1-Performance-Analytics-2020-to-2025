import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Overview from "./pages/Overview";
import Players from "./pages/Players";
import MatchHistory from "./pages/MatchHistory";
import MetaShifts from "./pages/MetaShifts";
import WinPrediction from "./pages/WinPrediction";
import Synergy from "./pages/Synergy";
import Admin from "./pages/Admin";
import Agent from "./pages/Agent";

export default function App() {
  return (
    <div className="min-h-screen bg-bg">
      <Navbar />
      <main className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/players" element={<Players />} />
          <Route path="/matches" element={<MatchHistory />} />
          <Route path="/meta-shifts" element={<MetaShifts />} />
          <Route path="/win-prediction" element={<WinPrediction />} />
          <Route path="/synergy" element={<Synergy />} />
          <Route path="/agent" element={<Agent />} />
          <Route path="/admin" element={<Admin />} />
        </Routes>
      </main>
    </div>
  );
}
