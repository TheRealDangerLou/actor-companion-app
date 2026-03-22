import { motion } from "framer-motion";
import { Sparkles, Layers } from "lucide-react";

const QUICK_PHASES = [
  "Reading your sides...",
  "Identifying beats and shifts...",
  "Crafting your takes...",
  "Building your breakdown...",
];

const DEEP_PHASES = [
  "Reading your sides closely...",
  "Mapping the emotional arc...",
  "Layering subtext — surface, meaning, fear...",
  "Finding what the character hides...",
  "Building director-level takes...",
  "Crafting your deep breakdown...",
];

export default function LoadingScreen({ mode = "quick", sceneProgress = null }) {
  const isDeep = mode === "deep";
  const phases = isDeep ? DEEP_PHASES : QUICK_PHASES;
  const duration = isDeep ? 120 : 60;
  const Icon = isDeep ? Layers : Sparkles;

  const isMultiScene = sceneProgress && sceneProgress.total > 1;

  return (
    <div
      data-testid="loading-screen"
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#09090b]"
    >
      {/* Spotlight effect */}
      <div className="absolute inset-0 overflow-hidden">
        <div className={`absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full blur-[100px] ${
          isDeep ? "bg-amber-500/[0.05]" : "bg-amber-500/[0.03]"
        }`} />
      </div>

      <div className="relative z-10 flex flex-col items-center">
        {/* Icon */}
        <motion.div
          animate={isDeep ? { scale: [1, 1.1, 1] } : { rotate: [0, 360] }}
          transition={isDeep
            ? { duration: 2, repeat: Infinity, ease: "easeInOut" }
            : { duration: 3, repeat: Infinity, ease: "linear" }
          }
          className="mb-8"
        >
          <Icon className="w-10 h-10 text-amber-500" />
        </motion.div>

        {/* Title */}
        <h2 className="font-display text-2xl md:text-3xl font-bold text-white mb-2 tracking-tight">
          {isMultiScene
            ? `Analyzing scene ${sceneProgress.current} of ${sceneProgress.total}`
            : isDeep ? "Deep scene study" : "Analyzing your scene"}
        </h2>

        {/* Scene heading */}
        {isMultiScene && sceneProgress.heading && (
          <p className="text-xs text-zinc-500 font-mono mb-2 max-w-xs truncate text-center">
            {sceneProgress.heading}
          </p>
        )}

        {/* Mode badge */}
        {isDeep && (
          <p className="text-xs text-amber-500/60 mb-6">
            Richer beats, layered subtext, tactical arc
          </p>
        )}
        {!isDeep && <div className="mb-6" />}

        {/* Phase text cycling */}
        <div className="h-6 mb-10 relative">
          {phases.map((phase, i) => (
            <motion.p
              key={phase}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: [0, 1, 1, 0], y: [8, 0, 0, -8] }}
              transition={{
                duration: 3.5,
                delay: i * 3.5,
                repeat: Infinity,
                repeatDelay: (phases.length - 1) * 3.5,
              }}
              className="text-sm text-zinc-500 absolute left-1/2 -translate-x-1/2 whitespace-nowrap"
            >
              {phase}
            </motion.p>
          ))}
        </div>

        {/* Progress bar */}
        {isMultiScene ? (
          <div className="w-48">
            <div className="h-1 bg-zinc-900 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-amber-500 rounded-full"
                initial={false}
                animate={{ width: `${(sceneProgress.current / sceneProgress.total) * 100}%` }}
                transition={{ duration: 0.5, ease: "easeOut" }}
              />
            </div>
            <p className="text-[10px] text-zinc-600 text-center mt-2 tabular-nums">
              {sceneProgress.current}/{sceneProgress.total} complete
            </p>
          </div>
        ) : (
          <div className="w-48 h-1 bg-zinc-900 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-amber-500 rounded-full"
              initial={{ width: "0%" }}
              animate={{ width: "100%" }}
              transition={{ duration, ease: "easeInOut" }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
