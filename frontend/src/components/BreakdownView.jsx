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
  onExportPdf,
  onNewAnalysis,
  onOpenMemorization,
}) {
  const [takesTab, setTakesTab] = useState("grounded");

  if (!breakdown) return null;

  const {
    scene_summary,
    character_name,
    character_objective,
    stakes,
    beats = [],
    acting_takes = {},
    self_tape_tips = {},
  } = breakdown;

  return (
    <div
      data-testid="breakdown-view"
      className="min-h-screen bg-[#09090b] pb-16"
    >
      {/* Header */}
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
              <span className="hidden sm:inline">New</span>
            </Button>
            <h1 className="font-display text-lg md:text-xl font-bold text-white truncate">
              {character_name || "Scene Breakdown"}
            </h1>
          </div>
          <div className="flex items-center gap-2">
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
              <TooltipContent>Export PDF</TooltipContent>
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
        </div>
      </header>

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
                        <Badge className="bg-zinc-800 text-zinc-400 border-0 text-xs hidden sm:inline-flex">
                          {beat.emotion}
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
                      <div className="bg-zinc-900/50 rounded-md p-3 border-l-2 border-amber-500/40">
                        <p className="text-xs uppercase tracking-wider text-zinc-500 mb-1">
                          Subtext (inner voice)
                        </p>
                        <p className="text-sm text-zinc-300 italic leading-relaxed font-script">
                          "{beat.subtext}"
                        </p>
                      </div>
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
    </div>
  );
}
