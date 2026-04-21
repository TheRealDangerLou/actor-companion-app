import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { ArrowLeft, Briefcase, Film, ChevronDown, ChevronUp, Calendar, Clock, Video, Users } from "lucide-react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ProjectCreate({ mode, onCreated, onBack }) {
  const [title, setTitle] = useState("");
  const [roleName, setRoleName] = useState("");
  const [auditionDate, setAuditionDate] = useState("");
  const [auditionTime, setAuditionTime] = useState("");
  const [auditionFormat, setAuditionFormat] = useState(null);
  const [saving, setSaving] = useState(false);
  const [showOptional, setShowOptional] = useState(false);

  const isAudition = mode === "audition";

  const handleCreate = useCallback(async () => {
    const trimmedTitle = title.trim();
    const trimmedRole = roleName.trim();
    if (!trimmedTitle) {
      toast.error("Give your project a name.");
      return;
    }
    if (!trimmedRole) {
      toast.error("Enter your character name.");
      return;
    }
    setSaving(true);
    try {
      const resp = await axios.post(`${API}/projects`, {
        title: trimmedTitle,
        role_name: trimmedRole,
        mode,
        audition_date: auditionDate || null,
        audition_time: auditionTime || null,
        audition_format: auditionFormat,
      });
      toast.success(`Project created.`);
      onCreated?.(resp.data);
    } catch {
      toast.error("Failed to create project.");
    }
    setSaving(false);
  }, [title, roleName, mode, auditionDate, auditionTime, auditionFormat, onCreated]);

  return (
    <div className="min-h-screen px-4 pb-24 pt-6 max-w-lg mx-auto" data-testid="project-create">
      {/* Back button */}
      <Button
        variant="ghost"
        size="sm"
        onClick={onBack}
        className="text-zinc-400 hover:text-zinc-200 gap-1 px-2 mb-6 -ml-2"
        data-testid="create-back-btn"
      >
        <ArrowLeft className="w-4 h-4" /> Back
      </Button>

      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
          isAudition ? "bg-amber-500/10" : "bg-blue-500/10"
        }`}>
          {isAudition
            ? <Briefcase className="w-5 h-5 text-amber-400" />
            : <Film className="w-5 h-5 text-blue-400" />
          }
        </div>
        <div>
          <h1 className="text-lg font-bold text-zinc-100">
            {isAudition ? "Create Audition" : "New Booked Role"}
          </h1>
        </div>
      </div>
      <p className="text-[13px] text-zinc-500 mb-7">Create your audition, then upload your sides.</p>

      {/* Form */}
      <div className="space-y-5">
        {/* Project / Show */}
        <div>
          <label className="block text-xs font-medium text-zinc-400 mb-1.5">
            Project / Show *
          </label>
          <Input
            placeholder={isAudition ? 'e.g. Night Shift' : 'e.g. If a Woman Wants — EP 1-4'}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="h-12 bg-zinc-900 border-zinc-800 text-zinc-200 rounded-xl text-sm"
            data-testid="project-title-input"
            autoFocus
          />
        </div>

        {/* Character */}
        <div>
          <label className="block text-xs font-medium text-zinc-400 mb-1.5">
            Character *
          </label>
          <Input
            placeholder='e.g. Jack'
            value={roleName}
            onChange={(e) => setRoleName(e.target.value)}
            className="h-12 bg-zinc-900 border-zinc-800 text-zinc-200 rounded-xl text-sm"
            data-testid="role-name-input"
          />
        </div>

        {/* Optional details toggle */}
        {isAudition && (
          <button
            onClick={() => setShowOptional((v) => !v)}
            className="flex items-center gap-1.5 text-[12px] text-zinc-500 hover:text-zinc-400 transition-colors"
            data-testid="toggle-optional-btn"
          >
            {showOptional ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            Optional details
          </button>
        )}

        {/* Audition date/time (collapsed by default) */}
        {isAudition && showOptional && (
          <>
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                  <Calendar className="w-3 h-3 inline mr-1" />
                  Date
                </label>
                <Input
                  type="date"
                  value={auditionDate}
                  onChange={(e) => setAuditionDate(e.target.value)}
                  className="h-12 bg-zinc-900 border-zinc-800 text-zinc-200 rounded-xl text-sm"
                  data-testid="audition-date-input"
                />
              </div>
              <div className="flex-1">
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                  <Clock className="w-3 h-3 inline mr-1" />
                  Time
                </label>
                <Input
                  type="time"
                  value={auditionTime}
                  onChange={(e) => setAuditionTime(e.target.value)}
                  className="h-12 bg-zinc-900 border-zinc-800 text-zinc-200 rounded-xl text-sm"
                  data-testid="audition-time-input"
                />
              </div>
            </div>

            {/* Audition format */}
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-2">
                Format
              </label>
              <div className="flex gap-3">
                <button
                  onClick={() => setAuditionFormat(auditionFormat === "self-tape" ? null : "self-tape")}
                  className={`flex-1 h-12 rounded-xl border text-sm font-medium flex items-center justify-center gap-2 transition-colors ${
                    auditionFormat === "self-tape"
                      ? "border-amber-500/40 bg-amber-500/10 text-amber-400"
                      : "border-zinc-800 bg-zinc-900 text-zinc-400 hover:border-zinc-700"
                  }`}
                  data-testid="format-self-tape"
                >
                  <Video className="w-4 h-4" />
                  Self-Tape
                </button>
                <button
                  onClick={() => setAuditionFormat(auditionFormat === "in-person" ? null : "in-person")}
                  className={`flex-1 h-12 rounded-xl border text-sm font-medium flex items-center justify-center gap-2 transition-colors ${
                    auditionFormat === "in-person"
                      ? "border-amber-500/40 bg-amber-500/10 text-amber-400"
                      : "border-zinc-800 bg-zinc-900 text-zinc-400 hover:border-zinc-700"
                  }`}
                  data-testid="format-in-person"
                >
                  <Users className="w-4 h-4" />
                  In-Person
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Create button */}
      <div className="mt-10">
        <Button
          onClick={handleCreate}
          disabled={saving || !title.trim() || !roleName.trim()}
          className="w-full h-14 bg-amber-500 hover:bg-amber-600 text-black font-semibold rounded-xl text-sm"
          data-testid="create-project-btn"
        >
          {saving ? "Creating..." : "Continue \u2192 Upload Sides"}
        </Button>
      </div>
    </div>
  );
}
