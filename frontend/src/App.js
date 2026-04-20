import { useState, useCallback } from "react";
import "@/App.css";
import axios from "axios";
import { Toaster, toast } from "sonner";
import { AnimatePresence, motion } from "framer-motion";
import { TooltipProvider } from "@/components/ui/tooltip";
import ProjectHome from "@/components/ProjectHome";
import ProjectCreate from "@/components/ProjectCreate";
import DocumentUpload from "@/components/DocumentUpload";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function App() {
  const [view, setView] = useState("home"); // "home" | "create" | "project"
  const [createMode, setCreateMode] = useState("audition");
  const [activeProject, setActiveProject] = useState(null);
  const [loading, setLoading] = useState(false);

  // --- Navigation handlers ---
  const handleCreateProject = useCallback((mode) => {
    setCreateMode(mode);
    setView("create");
  }, []);

  const handleProjectCreated = useCallback((project) => {
    setActiveProject(project);
    setView("project");
  }, []);

  const handleOpenProject = useCallback(async (projectId) => {
    setLoading(true);
    try {
      const resp = await axios.get(`${API}/projects/${projectId}`);
      setActiveProject(resp.data);
      setView("project");
    } catch {
      toast.error("Could not open project.");
    }
    setLoading(false);
  }, []);

  const handleDocumentsChanged = useCallback((docs, shouldContinue) => {
    setActiveProject((prev) => prev ? { ...prev, documents: docs } : prev);
    if (shouldContinue) {
      // Feature #4 will add the review/cleaning flow here
      toast.success("Documents saved. Review & cleaning coming next.");
      setView("home");
    }
  }, []);

  const handleBackToHome = useCallback(() => {
    setView("home");
    setActiveProject(null);
  }, []);

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-[#09090b] text-white">
        <AnimatePresence mode="wait">
          {loading && (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="min-h-screen flex items-center justify-center"
            >
              <div className="text-zinc-500 text-sm">Loading...</div>
            </motion.div>
          )}

          {!loading && view === "home" && (
            <motion.div key="home" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
              <ProjectHome onOpenProject={handleOpenProject} onCreateProject={handleCreateProject} />
            </motion.div>
          )}

          {!loading && view === "create" && (
            <motion.div key="create" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
              <ProjectCreate mode={createMode} onCreated={handleProjectCreated} onBack={handleBackToHome} />
            </motion.div>
          )}

          {!loading && view === "project" && activeProject && (
            <motion.div key="project" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
              <DocumentUpload
                project={activeProject}
                onDocumentsChanged={handleDocumentsChanged}
                onBack={handleBackToHome}
              />
            </motion.div>
          )}
        </AnimatePresence>

        <Toaster
          position="top-center"
          toastOptions={{
            style: { background: "#18181b", color: "#fafafa", border: "1px solid #27272a" },
          }}
        />
      </div>
    </TooltipProvider>
  );
}

export default App;
