import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Briefcase, Film, ChevronRight, Trash2, Calendar, FileText } from "lucide-react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ProjectHome({ onOpenProject, onCreateProject }) {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadProjects = useCallback(async () => {
    try {
      const resp = await axios.get(`${API}/projects`);
      setProjects(resp.data || []);
    } catch {
      toast.error("Failed to load projects.");
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const handleDelete = useCallback(async (e, projectId, title) => {
    e.stopPropagation();
    if (!window.confirm(`Delete "${title}"? This cannot be undone.`)) return;
    try {
      await axios.delete(`${API}/projects/${projectId}`);
      setProjects((prev) => prev.filter((p) => p.id !== projectId));
      toast.success("Project deleted.");
    } catch {
      toast.error("Failed to delete.");
    }
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" data-testid="home-loading">
        <div className="text-zinc-500 text-sm">Loading projects...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen px-4 pb-24 pt-6 max-w-lg mx-auto" data-testid="project-home">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-zinc-100 tracking-tight">
          Actor's Companion
        </h1>
        <p className="text-sm text-zinc-500 mt-1">Your audition command center.</p>
      </div>

      {/* New project buttons */}
      <div className="flex gap-3 mb-8">
        <Button
          onClick={() => onCreateProject("audition")}
          className="flex-1 h-14 bg-amber-500 hover:bg-amber-600 text-black font-semibold gap-2 rounded-xl text-sm"
          data-testid="new-audition-btn"
        >
          <Briefcase className="w-4 h-4" />
          New Audition
        </Button>
        <Button
          onClick={() => onCreateProject("booked")}
          variant="outline"
          className="flex-1 h-14 border-zinc-700 text-zinc-300 hover:bg-zinc-800 gap-2 rounded-xl text-sm"
          data-testid="new-booked-btn"
        >
          <Film className="w-4 h-4" />
          Booked Role
        </Button>
      </div>

      {/* Projects list */}
      {projects.length === 0 ? (
        <div className="text-center py-16" data-testid="empty-state">
          <div className="w-12 h-12 rounded-full bg-zinc-800 flex items-center justify-center mx-auto mb-4">
            <Plus className="w-5 h-5 text-zinc-500" />
          </div>
          <p className="text-zinc-400 text-sm">No projects yet.</p>
          <p className="text-zinc-600 text-xs mt-1">Create your first audition to get started.</p>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-xs text-zinc-500 uppercase tracking-wider font-medium mb-2">
            Your Projects
          </p>
          <AnimatePresence>
            {(Array.isArray(projects) ? projects : []).map((project) => (
              <motion.div
                key={project.id}
                layout
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -100 }}
                transition={{ duration: 0.2 }}
              >
                <div
                  onClick={() => onOpenProject(project.id)}
                  role="button"
                  tabIndex={0}
                  className="w-full text-left bg-zinc-900/60 border border-zinc-800/60 rounded-xl p-4 hover:bg-zinc-800/40 transition-colors group cursor-pointer"
                  data-testid={`project-card-${project.id}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide ${
                          project.mode === "audition"
                            ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                            : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                        }`}>
                          {project.mode}
                        </span>
                        {project.audition_date && (
                          <span className="text-[10px] text-zinc-500 flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {project.audition_date}
                          </span>
                        )}
                      </div>
                      <h3 className="text-sm font-semibold text-zinc-200 truncate">
                        {project.title}
                      </h3>
                      {project.role_name && (
                        <p className="text-xs text-zinc-500 mt-0.5">
                          Role: {project.role_name}
                        </p>
                      )}
                      <p className="text-xs text-zinc-600 mt-1">
                        {project.document_count || 0} document{project.document_count !== 1 ? "s" : ""}
                      </p>
                    </div>
                    <div className="flex items-center gap-1 ml-3 shrink-0">
                      <button
                        onClick={(e) => handleDelete(e, project.id, project.title)}
                        className="p-2 text-zinc-600 hover:text-red-400 transition-colors rounded-lg"
                        data-testid={`delete-project-${project.id}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                      <ChevronRight className="w-4 h-4 text-zinc-600 group-hover:text-zinc-400 transition-colors" />
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
