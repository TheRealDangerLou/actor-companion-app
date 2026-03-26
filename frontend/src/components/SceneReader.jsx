import { useState, useRef, useCallback, useEffect } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";
import axios from "axios";
import { toast } from "sonner";
import {
  X,
  Play,
  Pause,
  SkipForward,
  RotateCcw,
  Mic,
  Volume2,
  VolumeX,
  Clock,
  Loader2,
  ChevronDown,
  User,
} from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function useWakeLock() {
  const wakeLockRef = useRef(null);
  useEffect(() => {
    const request = async () => {
      try {
        if ("wakeLock" in navigator) {
          wakeLockRef.current = await navigator.wakeLock.request("screen");
        }
      } catch (e) { /* non-critical */ }
    };
    request();
    return () => { wakeLockRef.current?.release().catch(() => {}); };
  }, []);
}

export default function SceneReader({
  memorization,
  characterName,
  ttsAvailable,
  voices = [],
  onClose,
}) {
  const [currentCue, setCurrentCue] = useState(-1);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [pauseDuration, setPauseDuration] = useState(4);
  const [showYourLine, setShowYourLine] = useState(false);
  const [selectedVoice, setSelectedVoice] = useState(null);
  const [showVoicePicker, setShowVoicePicker] = useState(false);
  const audioRef = useRef(null);
  const abortRef = useRef(false);
  const timeoutRef = useRef(null);
  const cueRefs = useRef([]);
  const scrollContainerRef = useRef(null);

  useWakeLock();

  const cues = memorization?.cue_recall || [];

  // Auto-scroll to active cue
  useEffect(() => {
    if (currentCue >= 0 && cueRefs.current[currentCue]) {
      cueRefs.current[currentCue].scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }
  }, [currentCue]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortRef.current = true;
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = "";
      }
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  const playCueAudio = useCallback(async (text) => {
    if (!ttsAvailable) return false;
    setIsGenerating(true);
    try {
      const payload = { text };
      if (selectedVoice) payload.voice_id = selectedVoice;
      const response = await axios.post(`${API}/tts/generate`, payload, { timeout: 30000 });
      if (abortRef.current) { setIsGenerating(false); return false; }

      const audioUrl = response.data.audio_url;
      if (!audioUrl) { setIsGenerating(false); return false; }

      // Use a single reusable audio element to avoid iOS autoplay issues
      if (!audioRef.current) {
        audioRef.current = new Audio();
      }
      const audio = audioRef.current;
      audio.src = audioUrl;

      const played = await new Promise((resolve) => {
        // Timeout: if audio doesn't finish in 30s, move on
        const safetyTimeout = setTimeout(() => {
          console.warn("[SceneReader] Audio playback timed out");
          resolve(true);
        }, 30000);

        audio.onended = () => { clearTimeout(safetyTimeout); resolve(true); };
        audio.onerror = (e) => {
          clearTimeout(safetyTimeout);
          console.warn("[SceneReader] Audio error:", e);
          resolve(false);
        };

        audio.play().catch((err) => {
          clearTimeout(safetyTimeout);
          console.warn("[SceneReader] Audio play blocked:", err.message);
          resolve(false);
        });
      });

      setIsGenerating(false);
      return played;
    } catch (err) {
      if (!abortRef.current) {
        console.warn("[SceneReader] TTS request failed:", err.message);
      }
      setIsGenerating(false);
      return false;
    }
  }, [ttsAvailable, selectedVoice]);

  const waitForPause = useCallback(() => {
    return new Promise((resolve) => {
      timeoutRef.current = setTimeout(resolve, pauseDuration * 1000);
    });
  }, [pauseDuration]);

  const runLines = useCallback(async () => {
    abortRef.current = false;
    setIsPlaying(true);

    // Pre-initialize audio element on the first user gesture (iOS requirement)
    if (!audioRef.current) {
      audioRef.current = new Audio();
    }
    // Silent load to "unlock" audio on iOS
    try {
      audioRef.current.src = "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=";
      await audioRef.current.play();
      audioRef.current.pause();
    } catch (e) { /* expected on some browsers */ }

    for (let i = 0; i < cues.length; i++) {
      if (abortRef.current) break;

      setCurrentCue(i);
      setShowYourLine(false);

      const cueText = cues[i].cue;
      const cueSpeaker = (cues[i].cue_speaker || "").toUpperCase();
      const isSelfCue = cueSpeaker && characterName && cueSpeaker === characterName.toUpperCase();
      const isSceneStart = cueText === "(Scene start)";

      // Play the cue line (other character) via TTS — skip for scene start and self-cues
      if (ttsAvailable && !isSceneStart && !isSelfCue) {
        const audioPlayed = await playCueAudio(cueText);
        if (!audioPlayed && !abortRef.current) {
          await new Promise(r => { timeoutRef.current = setTimeout(r, 2000); });
        }
      } else {
        // Short pause for scene start / self-cue / no TTS
        await new Promise(r => { timeoutRef.current = setTimeout(r, isSceneStart ? 500 : 1500); });
      }

      if (abortRef.current) break;

      // Show your line after cue plays
      setShowYourLine(true);

      // Wait for the actor to perform
      await waitForPause();

      if (abortRef.current) break;
    }

    setIsPlaying(false);
    if (!abortRef.current) {
      setCurrentCue(cues.length);
      toast.success("Scene complete. Great work.");
    }
  }, [cues, ttsAvailable, playCueAudio, waitForPause]);

  const stopPlaying = useCallback(() => {
    abortRef.current = true;
    setIsPlaying(false);
    setIsGenerating(false);
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
    }
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
  }, []);

  const restart = useCallback(() => {
    stopPlaying();
    setCurrentCue(-1);
    setShowYourLine(false);
  }, [stopPlaying]);

  const skipToNext = useCallback(() => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
    }
    // Force advance: if currently waiting for audio/pause, the cleared timeout
    // will resolve the promise (via the abort check in runLines)
    if (currentCue < cues.length - 1) {
      setCurrentCue(prev => prev + 1);
      setShowYourLine(false);
    }
  }, [currentCue, cues.length]);

  const playSingleCue = useCallback(async (index) => {
    if (!ttsAvailable) return;
    const cueText = cues[index].cue;
    const cueSpeaker = (cues[index].cue_speaker || "").toUpperCase();
    const isSelfCue = cueSpeaker && characterName && cueSpeaker === characterName.toUpperCase();
    if (cueText === "(Scene start)" || isSelfCue) return;
    setCurrentCue(index);
    setShowYourLine(false);
    await playCueAudio(cueText);
    setShowYourLine(true);
  }, [ttsAvailable, cues, playCueAudio, characterName]);

  return (
    <motion.div
      data-testid="scene-reader-overlay"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.25 }}
      className="fixed inset-0 z-50 bg-[#09090b]/98 backdrop-blur-sm flex flex-col"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 sm:px-6 py-4 border-b border-zinc-900">
        <div className="flex items-center gap-3">
          <Mic className="w-5 h-5 text-emerald-400" />
          <h2 className="font-display text-lg font-bold text-white">
            Run Lines {characterName ? `— ${characterName}` : ""}
          </h2>
          {ttsAvailable ? (
            <Badge className="bg-emerald-900/30 text-emerald-400 border-emerald-800 text-xs">
              <Volume2 className="w-3 h-3 mr-1" /> Voice Active
            </Badge>
          ) : (
            <Badge variant="outline" className="text-zinc-500 border-zinc-700 text-xs">
              <VolumeX className="w-3 h-3 mr-1" /> Text Only
            </Badge>
          )}
        </div>
        <Button
          data-testid="scene-reader-close"
          variant="ghost"
          size="icon"
          onClick={() => { stopPlaying(); onClose(); }}
          className="text-zinc-400 hover:text-white"
        >
          <X className="w-5 h-5" />
        </Button>
      </div>

      {/* Controls */}
      <div className="px-4 sm:px-6 py-4 border-b border-zinc-900/50">
        <div className="max-w-2xl mx-auto flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            {!isPlaying ? (
              <Button
                data-testid="scene-reader-play"
                onClick={runLines}
                disabled={cues.length === 0}
                className="bg-emerald-600 hover:bg-emerald-700 text-white gap-2 btn-press"
              >
                <Play className="w-4 h-4" />
                {currentCue >= cues.length ? "Run Again" : "Run Lines"}
              </Button>
            ) : (
              <Button
                data-testid="scene-reader-stop"
                onClick={stopPlaying}
                className="bg-zinc-800 hover:bg-zinc-700 text-white gap-2 btn-press"
              >
                <Pause className="w-4 h-4" />
                Stop
              </Button>
            )}
            {isPlaying && (
              <Button
                data-testid="scene-reader-skip"
                variant="ghost"
                size="icon"
                onClick={skipToNext}
                className="text-zinc-400 hover:text-white"
                title="Skip to next"
              >
                <SkipForward className="w-4 h-4" />
              </Button>
            )}
            <Button
              data-testid="scene-reader-restart"
              variant="ghost"
              size="icon"
              onClick={restart}
              className="text-zinc-400 hover:text-white"
            >
              <RotateCcw className="w-4 h-4" />
            </Button>
          </div>

          <div className="flex items-center gap-2 ml-auto">
            <Clock className="w-3.5 h-3.5 text-zinc-500" />
            <span className="text-xs text-zinc-500">Pause</span>
            <Slider
              data-testid="scene-reader-pace-slider"
              value={[pauseDuration]}
              onValueChange={([v]) => setPauseDuration(v)}
              min={2}
              max={10}
              step={1}
              className="w-24"
            />
            <span className="text-xs text-zinc-400 w-6">{pauseDuration}s</span>
          </div>

          {isGenerating && (
            <div className="flex items-center gap-1.5 text-xs text-amber-500">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              Speaking...
            </div>
          )}
        </div>

        {/* Voice picker */}
        {ttsAvailable && voices.length > 0 && (
          <div className="max-w-2xl mx-auto mt-3 relative">
            <button
              data-testid="voice-picker-toggle"
              onClick={() => setShowVoicePicker(!showVoicePicker)}
              disabled={isPlaying}
              className="flex items-center gap-2 text-xs text-zinc-400 hover:text-zinc-200 transition-colors disabled:opacity-40"
            >
              <User className="w-3 h-3" />
              <span>{selectedVoice ? voices.find(v => v.voice_id === selectedVoice)?.name || "Custom" : "Rachel (default)"}</span>
              <ChevronDown className={`w-3 h-3 transition-transform ${showVoicePicker ? 'rotate-180' : ''}`} />
            </button>

            {showVoicePicker && !isPlaying && (
              <div
                data-testid="voice-picker-list"
                className="absolute top-full left-0 mt-1 w-72 max-h-52 overflow-y-auto bg-zinc-900 border border-zinc-800 rounded-lg shadow-xl z-50"
              >
                {voices.map((v) => (
                  <button
                    key={v.voice_id}
                    data-testid={`voice-option-${v.voice_id}`}
                    onClick={() => { setSelectedVoice(v.voice_id); setShowVoicePicker(false); }}
                    className={`w-full text-left px-3 py-2 flex items-center gap-3 hover:bg-zinc-800 transition-colors ${
                      selectedVoice === v.voice_id ? 'bg-zinc-800/60' : ''
                    }`}
                  >
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm font-medium ${selectedVoice === v.voice_id ? 'text-emerald-400' : 'text-zinc-200'}`}>
                        {v.name}
                      </p>
                      <p className="text-[10px] text-zinc-500">{v.gender} · {v.accent} · {v.style}</p>
                    </div>
                    {selectedVoice === v.voice_id && (
                      <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Progress indicator */}
      {isPlaying && cues.length > 0 && (
        <div className="px-4 sm:px-6 py-2 border-b border-zinc-900/30">
          <div className="max-w-2xl mx-auto flex items-center gap-2">
            <span className="text-xs text-zinc-600 tabular-nums">{Math.min(currentCue + 1, cues.length)}/{cues.length}</span>
            <div className="flex-1 h-0.5 bg-zinc-900 rounded-full overflow-hidden">
              <div
                className="h-full bg-emerald-500 rounded-full transition-all duration-300"
                style={{ width: `${((currentCue + 1) / cues.length) * 100}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Scene Content */}
      <div ref={scrollContainerRef} className="flex-1 overflow-y-auto px-4 sm:px-6 py-4 sm:py-6 mobile-bottom-safe">
        <div className="max-w-2xl mx-auto space-y-3">
          {!ttsAvailable && (
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4 mb-4 sm:mb-6">
              <p className="text-sm text-zinc-400">
                <span className="text-amber-500 font-semibold">Voice not connected.</span>{" "}
                Add your ElevenLabs API key to hear the other character read their lines. For now, use the text cues below.
              </p>
            </div>
          )}

          {currentCue === -1 && !isPlaying && (
            <div className="text-center py-12">
              <p className="text-zinc-500 text-sm">
                Press <span className="text-emerald-400 font-semibold">Run Lines</span> to start.
                {ttsAvailable
                  ? " The AI reader will speak the other character's lines."
                  : " Read each cue, then perform your response."}
              </p>
            </div>
          )}

          {cues.map((item, i) => {
            const isActive = i === currentCue;
            const isPast = i < currentCue;
            const isFuture = i > currentCue;

            return (
              <motion.div
                key={i}
                ref={(el) => (cueRefs.current[i] = el)}
                initial={false}
                animate={{
                  opacity: isFuture ? 0.25 : 1,
                  scale: isActive ? 1 : 0.98,
                }}
                transition={{ duration: 0.3 }}
                className={`rounded-lg border overflow-hidden transition-colors ${
                  isActive
                    ? "border-emerald-700/50 bg-zinc-900/60"
                    : isPast
                    ? "border-zinc-800/30 bg-zinc-950/30"
                    : "border-zinc-900 bg-zinc-950/20"
                }`}
                data-testid={`scene-reader-cue-${i}`}
              >
                {/* Cue Line (other character) */}
                <div className="px-4 py-3 border-b border-zinc-800/30 flex items-start gap-3">
                  <div className="flex-1">
                    <p className="text-xs uppercase tracking-wider text-zinc-600 mb-1">
                      {item.cue === "(Scene start)" ? "Scene Start" : 
                       item.cue_speaker && characterName && item.cue_speaker.toUpperCase() === characterName.toUpperCase() 
                         ? "Your Previous Line" : "Cue"}
                    </p>
                    <p className={`text-sm sm:text-base font-script ${isActive ? 'text-zinc-200' : 'text-zinc-400'} ${
                      item.cue === "(Scene start)" ? 'italic text-zinc-600' : ''
                    }`}>
                      {item.cue === "(Scene start)" ? "You speak first." : item.cue}
                    </p>
                  </div>
                  {ttsAvailable && !isPlaying && (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => playSingleCue(i)}
                      className="text-zinc-500 hover:text-emerald-400 shrink-0 mt-2"
                      data-testid={`scene-reader-play-cue-${i}`}
                    >
                      <Play className="w-3.5 h-3.5" />
                    </Button>
                  )}
                </div>

                {/* Your Line */}
                <div className="px-4 py-3">
                  <p className="text-xs uppercase tracking-wider text-amber-500/60 mb-1">Your Line</p>
                  <p
                    className={`font-script text-base sm:text-lg transition-all duration-300 ${
                      isActive && !showYourLine
                        ? "text-zinc-100 blur-sm select-none"
                        : isActive && showYourLine
                        ? "text-amber-100 reader-line-active py-1"
                        : "text-zinc-400"
                    }`}
                  >
                    {item.your_line}
                  </p>
                  {isActive && !showYourLine && isPlaying && (
                    <p className="text-xs text-zinc-600 mt-1 italic">Listening...</p>
                  )}
                  {isActive && showYourLine && isPlaying && (
                    <p className="text-xs text-amber-500/60 mt-1 italic">Your turn — perform it.</p>
                  )}
                </div>
              </motion.div>
            );
          })}

          {currentCue >= cues.length && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center py-8"
            >
              <p className="text-emerald-400 font-semibold mb-2">Scene complete.</p>
              <p className="text-sm text-zinc-500">
                Run it again, adjust the pacing, or try a different take.
              </p>
            </motion.div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
