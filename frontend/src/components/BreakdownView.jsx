import { useState } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Film,
  Target,
  Flame,
  Layers,
  Camera,
  RefreshCw,
  Download,
  BookOpen,
  ArrowLeft,
  Zap,
  CircleDot,
  Shuffle,
  Share2,
  Mic,
  ExternalLink,
  Printer,
  TrendingUp,
  EyeOff,
  Sparkles,
} from "lucide-react";

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08 } },
};
const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4 } },
};

function highlightKeywords(text, keywords = []) {
  if (!keywords || keywords.length === 0) return text;
  const regex = new RegExp(`\\b(${keywords.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join("|")})\\b`, "gi");
  const parts = text.split(regex);
  return parts.map((part, i) =>
    keywords.some((k) => k.toLowerCase() === part.toLowerCase()) ? (
      <span key={i} className="keyword-highlight">{part}</span>
    ) : (
      part
    )
  );
}

export default function BreakdownView({
  breakdown,
  onRegenerate,
  onReanalyzeDeep,
  onExportPdf,
  onNewAnalysis,
  onOpenMemorization,
  onOpenSceneReader,
  onShare,
  ttsAvailable,
  isShareView = false,
  hideHeader = false,
}) {
  const [takesTab, setTakesTab] = useState("grounded");

  if (!breakdown) return null;

  const {
    scene_summary,
    character_name,
    character_objective,
    stakes,
    emotional_arc,
    what_they_hide,
    beats = [],
    acting_takes = {},
    self_tape_tips = {},
    _debug,
    mode,
  } = breakdown;

  const isFallback = _debug?.fallback;
  const isDeep = mode === "deep" || !!emotional_arc;

  return (
    <div
      data-testid="breakdown-view"
      className={hideHeader ? "pb-16" : "min-h-screen bg-[#09090b] pb-16"}
    >
      {/* Debug/Fallback Banner */}
      {isFallback && (
        <div data-testid="fallback-banner" className="bg-amber-900/30 border-b border-amber-700/50 px-4 py-3">
          <div className="max-w-5xl mx-auto">
            <p className="text-amber-400 text-sm font-medium">Analysis incomplete — partial results shown</p>
            <p className="text-amber-500/70 text-xs mt-1">{_debug?.reason}</p>
            <details className="mt-2">
              <summary className="text-xs text-amber-600 cursor-pointer hover:text-amber-400">Pipeline stages</summary>
              <pre className="text-xs text-amber-700 mt-1 whitespace-pre-wrap font-mono">
                {JSON.stringify(_debug?.stages, null, 2)}
              </pre>
            </details>
          </div>
        </div>
      )}
      {/* Header */}
      {!hideHeader && (
      <header className="sticky top-0 z-40 bg-[#09090b]/90 backdrop-blur-md border-b border-zinc-900">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <Button
              data-testid="new-analysis-button"
              variant="ghost"
              size="sm"
              onClick={onNewAnalysis}
              className="text-zinc-400 hover:text-white shrink-0"
            >
              <ArrowLeft className="w-4 h-4 mr-1" />
              <span className="hidden sm:inline">{isShareView ? "Create Yours" : "New"}</span>
            </Button>
            <h1 className="font-display text-lg md:text-xl font-bold text-white truncate">
              {character_name || "Scene Breakdown"}
            </h1>
            {isDeep && (
              <Badge className="bg-amber-500/10 text-amber-500 border border-amber-500/20 text-[10px] shrink-0">
                DEEP
              </Badge>
            )}
          </div>
          {!isShareView && (
            <div className="flex items-center gap-1.5">
              {onOpenSceneReader && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      data-testid="scene-reader-button"
                      variant="ghost"
                      size="icon"
                      onClick={onOpenSceneReader}
                      className={`text-zinc-400 ${ttsAvailable ? 'hover:text-emerald-400' : 'hover:text-amber-500'}`}
                    >
                      <Mic className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>{ttsAvailable ? "Run Lines (AI Reader)" : "Run Lines"}</TooltipContent>
                </Tooltip>
              )}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    data-testid="memorization-button"
                    variant="ghost"
                    size="icon"
                    onClick={onOpenMemorization}
                    className="text-zinc-400 hover:text-amber-500"
                  >
                    <BookOpen className="w-4 h-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Reader Mode</TooltipContent>
              </Tooltip>
              {onShare && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      data-testid="share-button"
                      variant="ghost"
                      size="icon"
                      onClick={onShare}
                      className="text-zinc-400 hover:text-amber-500"
                    >
                      <Share2 className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Share Breakdown</TooltipContent>
                </Tooltip>
              )}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    data-testid="export-pdf-button"
                    variant="ghost"
                    size="icon"
                    onClick={onExportPdf}
                    className="text-zinc-400 hover:text-amber-500"
                  >
                    <Download className="w-4 h-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Download PDF</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    data-testid="print-button"
                    variant="ghost"
                    size="icon"
                    onClick={() => window.print()}
                    className="text-zinc-400 hover:text-amber-500"
                  >
                    <Printer className="w-4 h-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Print Breakdown</TooltipContent>
              </Tooltip>
              <Button
                data-testid="regenerate-takes-button"
                variant="ghost"
                size="sm"
                onClick={onRegenerate}
                className="text-zinc-400 hover:text-amber-500 gap-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">New Takes</span>
              </Button>
            </div>
          )}
          {isShareView && (
            <div className="flex items-center gap-2">
              <a
                href="/"
                data-testid="share-cta-button"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-black text-sm font-bold rounded-md transition-colors btn-press"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                Get Your Breakdown
              </a>
            </div>
          )}
        </div>
      </header>
      )}

      {/* Re-analyze in Deep CTA — only for Quick breakdowns */}
      {!isShareView && !isDeep && onReanalyzeDeep && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.4 }}
          className="max-w-5xl mx-auto px-4 sm:px-6 pt-5"
        >
          <button
            data-testid="reanalyze-deep-button"
            onClick={onReanalyzeDeep}
            className="w-full group relative overflow-hidden rounded-lg border border-amber-500/20 bg-gradient-to-r from-zinc-900 via-zinc-900 to-zinc-900 hover:border-amber-500/40 transition-all duration-300 px-5 py-3.5 text-left"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-amber-500/5 via-amber-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            <div className="relative flex items-center justify-between gap-4">
              <div className="flex items-center gap-3 min-w-0">
                <div className="shrink-0 w-8 h-8 rounded-full bg-amber-500/10 flex items-center justify-center">
                  <Sparkles className="w-4 h-4 text-amber-500" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-zinc-200 group-hover:text-white transition-colors">
                    Go Deeper
                  </p>
                  <p className="text-xs text-zinc-500 truncate">
                    Re-analyze with tactical arc, layered subtext & physical life
                  </p>
                </div>
              </div>
              <Badge className="bg-amber-500/10 text-amber-500 border-amber-500/20 text-[10px] shrink-0 group-hover:bg-amber-500/20 transition-colors">
                DEEP
              </Badge>
            </div>
          </button>
        </motion.div>
      )}

      {/* Content */}
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="max-w-5xl mx-auto px-4 sm:px-6 pt-8 grid grid-cols-1 md:grid-cols-2 gap-5"
      >
        {/* Scene Summary - full width */}
        <motion.div variants={item} className="md:col-span-2">
          <Card
            data-testid="scene-summary-card"
            className="card-spotlight bg-zinc-950/50 border-zinc-800"
          >
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-sm uppercase tracking-widest text-amber-500/80">
                <Film className="w-4 h-4" />
                Scene Summary
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-base md:text-lg text-zinc-200 leading-relaxed">
                {scene_summary}
              </p>
            </CardContent>
          </Card>
        </motion.div>

        {/* Objective */}
        <motion.div variants={item}>
          <Card
            data-testid="character-objective-card"
            className="card-spotlight bg-zinc-950/50 border-zinc-800 h-full"
          >
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-sm uppercase tracking-widest text-amber-500/80">
                <Target className="w-4 h-4" />
                Objective
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-zinc-200 leading-relaxed">
                {character_objective}
              </p>
            </CardContent>
          </Card>
        </motion.div>

        {/* Stakes */}
        <motion.div variants={item}>
          <Card
            data-testid="stakes-card"
            className="card-spotlight bg-zinc-950/50 border-zinc-800 h-full"
          >
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-sm uppercase tracking-widest text-rose-500/80">
                <Flame className="w-4 h-4" />
                Stakes
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-zinc-200 leading-relaxed">{stakes}</p>
            </CardContent>
          </Card>
        </motion.div>

        {/* Deep Mode: Emotional Arc + What They Hide */}
        {isDeep && emotional_arc && (
          <motion.div variants={item} className="md:col-span-2">
            <Card
              data-testid="emotional-arc-card"
              className="card-spotlight bg-zinc-950/50 border-zinc-800"
            >
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-sm uppercase tracking-widest text-amber-500/80">
                  <TrendingUp className="w-4 h-4" />
                  Tactical Arc
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-zinc-200 leading-relaxed">{emotional_arc}</p>
              </CardContent>
            </Card>
          </motion.div>
        )}
        {isDeep && what_they_hide && (
          <motion.div variants={item} className="md:col-span-2">
            <Card
              data-testid="what-they-hide-card"
              className="card-spotlight bg-zinc-950/50 border-zinc-800"
            >
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-sm uppercase tracking-widest text-rose-400/80">
                  <EyeOff className="w-4 h-4" />
                  What They Hide
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-zinc-200 leading-relaxed italic">{what_they_hide}</p>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Beat Breakdown - full width */}
        <motion.div variants={item} className="md:col-span-2">
          <Card
            data-testid="beat-breakdown-card"
            className="card-spotlight bg-zinc-950/50 border-zinc-800"
          >
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-sm uppercase tracking-widest text-amber-500/80">
                <Layers className="w-4 h-4" />
                Beat Breakdown
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Accordion type="single" collapsible className="space-y-2">
                {beats.map((beat) => (
                  <AccordionItem
                    key={beat.beat_number}
                    value={`beat-${beat.beat_number}`}
                    className="border border-zinc-800/50 rounded-lg px-4 data-[state=open]:bg-zinc-900/30"
                    data-testid={`beat-item-${beat.beat_number}`}
                  >
                    <AccordionTrigger className="hover:no-underline py-3">
                      <div className="flex items-center gap-3 text-left">
                        <Badge
                          variant="outline"
                          className="rounded-full bg-zinc-900 text-amber-500 border-amber-500/20 text-xs shrink-0"
                        >
                          {beat.beat_number}
                        </Badge>
                        <span className="font-semibold text-zinc-200">
                          {beat.title}
                        </span>
                        <Badge className="bg-zinc-800 text-zinc-400 border-0 text-xs hidden sm:inline-flex max-w-[200px] truncate">
                          {beat.behavior || beat.emotion || ""}
                        </Badge>
                      </div>
                    </AccordionTrigger>
                    <AccordionContent className="pb-4 space-y-3">
                      <p className="text-sm text-zinc-300 leading-relaxed">
                        {highlightKeywords(
                          beat.description,
                          beat.key_words
                        )}
                      </p>
                      {/* Behavior + Effect (v3 prompts) */}
                      {(beat.behavior || beat.effect) && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          {beat.behavior && (
                            <div className="bg-zinc-900/50 rounded-md p-3 border-l-2 border-amber-500/40">
                              <p className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1">What they do</p>
                              <p className="text-sm text-zinc-300 leading-relaxed">{beat.behavior}</p>
                            </div>
                          )}
                          {beat.effect && (
                            <div className="bg-zinc-900/50 rounded-md p-3 border-l-2 border-zinc-500/40">
                              <p className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1">How it lands</p>
                              <p className="text-sm text-zinc-400 leading-relaxed">{beat.effect}</p>
                            </div>
                          )}
                        </div>
                      )}
                      {/* Layered subtext (Deep) vs single subtext (Quick) */}
                      {beat.subtext_surface || beat.subtext_meaning || beat.subtext_fear ? (
                        <div className="space-y-2">
                          {beat.subtext_surface && (
                            <div className="bg-zinc-900/50 rounded-md p-3 border-l-2 border-zinc-600/40">
                              <p className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1">On the surface</p>
                              <p className="text-sm text-zinc-400 leading-relaxed font-script">"{beat.subtext_surface}"</p>
                            </div>
                          )}
                          {beat.subtext_meaning && (
                            <div className="bg-zinc-900/50 rounded-md p-3 border-l-2 border-amber-500/40">
                              <p className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1">What it does</p>
                              <p className="text-sm text-zinc-300 italic leading-relaxed font-script">"{beat.subtext_meaning}"</p>
                            </div>
                          )}
                          {beat.subtext_fear && (
                            <div className="bg-zinc-900/50 rounded-md p-3 border-l-2 border-rose-500/40">
                              <p className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1">If this fails</p>
                              <p className="text-sm text-zinc-300 italic leading-relaxed font-script">"{beat.subtext_fear}"</p>
                            </div>
                          )}
                        </div>
                      ) : beat.subtext ? (
                        <div className="bg-zinc-900/50 rounded-md p-3 border-l-2 border-amber-500/40">
                          <p className="text-xs uppercase tracking-wider text-zinc-500 mb-1">
                            Subtext
                          </p>
                          <p className="text-sm text-zinc-300 italic leading-relaxed font-script">
                            "{beat.subtext}"
                          </p>
                        </div>
                      ) : null}
                      {/* Physical life (Deep mode) */}
                      {beat.physical_life && (
                        <div className="bg-zinc-900/50 rounded-md p-3 border-l-2 border-emerald-500/40">
                          <p className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1">Physical life</p>
                          <p className="text-sm text-zinc-300 leading-relaxed">{beat.physical_life}</p>
                        </div>
                      )}
                      {beat.key_words?.length > 0 && (
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs text-zinc-500">
                            Land on:
                          </span>
                          {beat.key_words.map((kw) => (
                            <Badge
                              key={kw}
                              variant="outline"
                              className="text-amber-500 border-amber-500/20 text-xs"
                            >
                              {kw}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            </CardContent>
          </Card>
        </motion.div>

        {/* Acting Takes - full width */}
        <motion.div variants={item} className="md:col-span-2">
          <Card
            data-testid="acting-takes-card"
            className="card-spotlight bg-zinc-950/50 border-zinc-800"
          >
            <CardHeader className="pb-3 flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-sm uppercase tracking-widest text-amber-500/80">
                <Zap className="w-4 h-4" />
                Your Takes
              </CardTitle>
              {!isShareView && (
                <Button
                  data-testid="regenerate-takes-inline"
                  variant="ghost"
                  size="sm"
                  onClick={onRegenerate}
                  className="text-xs text-zinc-500 hover:text-amber-500 gap-1"
                >
                  <RefreshCw className="w-3 h-3" />
                  Regenerate
                </Button>
              )}
            </CardHeader>
            <CardContent>
              <Tabs
                value={takesTab}
                onValueChange={setTakesTab}
                className="w-full"
              >
                <TabsList className="w-full bg-zinc-900/80 border border-zinc-800 mb-4">
                  <TabsTrigger
                    value="grounded"
                    data-testid="take-grounded-tab"
                    className="flex-1 gap-1.5 text-xs sm:text-sm data-[state=active]:bg-zinc-800 data-[state=active]:text-emerald-400"
                  >
                    <CircleDot className="w-3.5 h-3.5" />
                    Grounded
                  </TabsTrigger>
                  <TabsTrigger
                    value="bold"
                    data-testid="take-bold-tab"
                    className="flex-1 gap-1.5 text-xs sm:text-sm data-[state=active]:bg-zinc-800 data-[state=active]:text-amber-400"
                  >
                    <Zap className="w-3.5 h-3.5" />
                    Bold
                  </TabsTrigger>
                  <TabsTrigger
                    value="wildcard"
                    data-testid="take-wildcard-tab"
                    className="flex-1 gap-1.5 text-xs sm:text-sm data-[state=active]:bg-zinc-800 data-[state=active]:text-rose-400"
                  >
                    <Shuffle className="w-3.5 h-3.5" />
                    Wildcard
                  </TabsTrigger>
                </TabsList>

                {["grounded", "bold", "wildcard"].map((key) => (
                  <TabsContent key={key} value={key}>
                    <div className="bg-zinc-900/30 rounded-lg p-5 border border-zinc-800/50">
                      <p
                        className="text-zinc-200 leading-relaxed whitespace-pre-line"
                        data-testid={`take-${key}-content`}
                      >
                        {acting_takes[key]}
                      </p>
                    </div>
                  </TabsContent>
                ))}
              </Tabs>
            </CardContent>
          </Card>
        </motion.div>

        {/* Self-Tape Tips - full width */}
        <motion.div variants={item} className="md:col-span-2">
          <Card
            data-testid="self-tape-tips-card"
            className="card-spotlight bg-zinc-950/50 border-zinc-800"
          >
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-sm uppercase tracking-widest text-amber-500/80">
                <Camera className="w-4 h-4" />
                Self-Tape Setup
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {[
                  {
                    label: "Framing",
                    value: self_tape_tips.framing,
                    testid: "tip-framing",
                  },
                  {
                    label: "Eyeline",
                    value: self_tape_tips.eyeline,
                    testid: "tip-eyeline",
                  },
                  {
                    label: "Tone & Energy",
                    value: self_tape_tips.tone_energy,
                    testid: "tip-tone",
                  },
                ].map(({ label, value, testid }) => (
                  <div
                    key={label}
                    data-testid={testid}
                    className="bg-zinc-900/40 rounded-lg p-4 border border-zinc-800/50"
                  >
                    <p className="text-xs uppercase tracking-wider text-zinc-500 mb-2">
                      {label}
                    </p>
                    <p className="text-sm text-zinc-300 leading-relaxed">
                      {value}
                    </p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>

      {/* Footer signature */}
      {!hideHeader && (
        <p className="text-center text-[10px] text-zinc-700/50 pb-4 pt-2">
          Co-produced by DangerLou Media
        </p>
      )}
    </div>
  );
}
