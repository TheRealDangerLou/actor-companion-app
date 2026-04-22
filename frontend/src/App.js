import { useState, useCallback } from "react";
import "@/App.css";
import axios from "axios";
import { Toaster, toast } from "sonner";
import { AnimatePresence, motion } from "framer-motion";
import { TooltipProvider } from "@/components/ui/tooltip";
import ProjectHome from "@/components/ProjectHome";
import ProjectCreate from "@/components/ProjectCreate";
import DocumentUpload from "@/components/DocumentUpload";
import DocumentReview from "@/components/DocumentReview";
import CharacterSelect from "@/components/CharacterSelect";
import PrepView from "@/components/PrepView";
import LineReview from "@/components/LineReview";
import BreakdownView from "@/components/BreakdownView";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function App() {
  const [view, setView] = useState("home"); // "home" | "create" | "project" | "review" | "characters" | "lines" | "prep" | "breakdown"
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
      const proj = resp.data;
      setActiveProject(proj);
      const docs = proj.documents || [];
      if (docs.length === 0) {
        setView("project");
      } else {
        const allConfirmed = docs.every((d) => d.is_confirmed);
        if (!allConfirmed) {
          setView("project");
        } else if (proj.selected_character) {
          const ct = proj.content_type;
          if (ct === "breakdown") {
            setView("breakdown");
          } else if (proj.reviewed_lines && proj.reviewed_lines.length > 0) {
            setView("prep");
          } else {
            setView("lines");
          }
        } else {
          setView("characters");
        }
      }
    } catch {
      toast.error("Could not open project.");
    }
    setLoading(false);
  }, []);

  const handleDocumentsChanged = useCallback((docs, shouldContinue) => {
    setActiveProject((prev) => prev ? { ...prev, documents: docs } : prev);
    if (shouldContinue) {
      setView("review");
    }
  }, []);

  const handleAllConfirmed = useCallback(async () => {
    // Detect content type before routing
    try {
      const resp = await axios.post(`${API}/projects/${activeProject.id}/detect-content-type`);
      const ct = resp.data.content_type;
      setActiveProject((prev) => prev ? { ...prev, content_type: ct } : prev);
      if (ct === "breakdown") {
        // For breakdowns, auto-use the role_name as selected_character (skip CharacterSelect)
        const roleName = activeProject.role_name?.trim();
        if (roleName) {
          await axios.put(`${API}/projects/${activeProject.id}`, { selected_character: roleName.toUpperCase() });
          setActiveProject((prev) => prev ? { ...prev, selected_character: roleName.toUpperCase() } : prev);
          setView("breakdown");
        } else {
          // No role name — still need character selection
          setView("characters");
        }
        return;
      }
    } catch {}
    setView("characters");
  }, [activeProject]);

  const handleCharacterSelected = useCallback(async (name) => {
    setActiveProject((prev) => prev ? { ...prev, selected_character: name } : prev);
    // Check if content_type was already detected
    const ct = activeProject?.content_type;
    if (ct === "breakdown") {
      setView("breakdown");
    } else if (!ct) {
      // Detect if not yet done
      try {
        const resp = await axios.post(`${API}/projects/${activeProject.id}/detect-content-type`);
        setActiveProject((prev) => prev ? { ...prev, content_type: resp.data.content_type } : prev);
        if (resp.data.content_type === "breakdown") {
          setView("breakdown");
          return;
        }
      } catch {}
      setView("lines");
    } else {
      setView("lines");
    }
  }, [activeProject]);

  const handleLinesReviewed = useCallback(() => {
    setView("prep");
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

          {!loading && view === "review" && activeProject && (
            <motion.div key="review" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
              <DocumentReview
                project={activeProject}
                onAllConfirmed={handleAllConfirmed}
                onBack={() => setView("project")}
              />
            </motion.div>
          )}

          {!loading && view === "characters" && activeProject && (
            <motion.div key="characters" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
              <CharacterSelect
                project={activeProject}
                onCharacterSelected={handleCharacterSelected}
                onBack={() => setView("review")}
              />
            </motion.div>
          )}

          {!loading && view === "lines" && activeProject && (
            <motion.div key="lines" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
              <LineReview
                project={activeProject}
                onLinesReviewed={handleLinesReviewed}
                onBack={() => setView("characters")}
              />
            </motion.div>
          )}

          {!loading && view === "prep" && activeProject && (
            <motion.div key="prep" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
              <PrepView
                project={activeProject}
                onBack={handleBackToHome}
                onChangeCharacter={() => setView("characters")}
                onEditLines={() => setView("lines")}
              />
            </motion.div>
          )}

          {!loading && view === "breakdown" && activeProject && (
            <motion.div key="breakdown" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
              <BreakdownView
                project={activeProject}
                onBack={handleBackToHome}
                onChangeCharacter={() => setView("characters")}
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
