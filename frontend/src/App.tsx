import { useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { Banner, Footer, HealthProvider, Nav } from "./components/Chrome";
import ErrorBoundary from "./components/ErrorBoundary";
import { Blobs } from "./components/ui";
import Board from "./pages/Board";
import CharterDetail from "./pages/CharterDetail";
import Charters from "./pages/Charters";
import Checks from "./pages/Checks";
import Home from "./pages/Home";
import IncidentDetail from "./pages/IncidentDetail";
import NewCharter from "./pages/NewCharter";
import OpenIncident from "./pages/OpenIncident";

function ScrollToTop() {
  const { pathname } = useLocation();
  // Block body, not a concise arrow: a concise arrow returns window.scrollTo's
  // value, React takes it as the cleanup function, and the tree unmounts with
  // "destroy is not a function". typecheck and build both pass either way.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

export default function App() {
  return (
    <ErrorBoundary>
      <HealthProvider>
        <Blobs />
        <ScrollToTop />
        <Nav />
        <Banner />
        <main className="min-h-[70vh]">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/app/charters" element={<Charters />} />
            <Route path="/app/charters/new" element={<NewCharter />} />
            <Route path="/app/charters/:id" element={<CharterDetail />} />
            <Route path="/app/board" element={<Board />} />
            <Route path="/app/incidents/new" element={<OpenIncident />} />
            <Route path="/app/incidents/:id" element={<IncidentDetail />} />
            <Route path="/app/checks" element={<Checks />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <Footer />
      </HealthProvider>
    </ErrorBoundary>
  );
}
