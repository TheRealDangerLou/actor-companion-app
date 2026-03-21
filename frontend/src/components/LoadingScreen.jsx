import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";

const PHASES = [
  "Reading your sides...",
  "Identifying beats and shifts...",
  "Crafting your takes...",
  "Building your breakdown...",
  "Almost there — polishing your notes...",
];

export default function LoadingScreen() {
  return (
    <div
      data-testid="loading-screen"
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#09090b]"
    >
      {/* Spotlight effect */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-amber-500/[0.03] blur-[100px]" />
      </div>

      <div className="relative z-10 flex flex-col items-center">
        {/* Icon */}
        <motion.div
          animate={{ rotate: [0, 360] }}
          transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
          className="mb-8"
        >
          <Sparkles className="w-10 h-10 text-amber-500" />
        </motion.div>

        {/* Title */}
        <h2 className="font-display text-2xl md:text-3xl font-bold text-white mb-8 tracking-tight">
          Analyzing your scene
        </h2>

        {/* Phase text cycling */}
        <div className="h-6 mb-10">
          {PHASES.map((phase, i) => (
            <motion.p
              key={phase}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: [0, 1, 1, 0], y: [8, 0, 0, -8] }}
              transition={{
                duration: 3,
                delay: i * 3,
                repeat: Infinity,
                repeatDelay: (PHASES.length - 1) * 3,
              }}
              className="text-sm text-zinc-500 absolute left-1/2 -translate-x-1/2"
            >
              {phase}
            </motion.p>
          ))}
        </div>

        {/* Progress bar */}
        <div className="w-48 h-1 bg-zinc-900 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-amber-500 rounded-full"
            initial={{ width: "0%" }}
            animate={{ width: "100%" }}
            transition={{ duration: 90, ease: "easeInOut" }}
          />
        </div>
      </div>
    </div>
  );
}
