// frontend-app/src/App.tsx
import { AnimatePresence, motion } from "framer-motion";
import { PatientCard } from "./components/PatientCard";
import { RecoveryStatus } from "./components/RecoveryStatus";
import { VoiceVisualizer } from "./components/VoiceVisualizer";
import { TranscriptViewer } from "./components/TranscriptViewer";
import { RiskAssessment } from "./components/RiskAssessment";
import { AgentTimeline } from "./components/AgentTimeline";
import { EvidencePanel } from "./components/EvidencePanel";
import { ActionButtons } from "./components/ActionButtons";
import { CallSummaryCard } from "./components/CallSummaryCard";
import { useVoiceCall } from "./hooks/useVoiceCall";
import { postSummary } from "./api";
import type { CallSummary } from "./types";
import { useCallback, useRef, useState } from "react";

const DEFAULT_PACIENTE_ID = "P001";
const NO_SYMPTOM_RATIONALES = new Set([
  "sin síntomas relevantes",
  "sin hallazgos",
]);

interface Toast {
  id: number;
  message: string;
  kind: "success" | "error";
}

export default function App() {
  const {
    state,
    turns,
    decision,
    patient,
    retrieval,
    startListening,
    stopAndSend,
    callId,
  } = useVoiceCall(DEFAULT_PACIENTE_ID);
  const recording = state === "listening";
  const [summary, setSummary] = useState<CallSummary | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const toastIdRef = useRef(0);

  const symptoms = Array.from(
    new Set(
      turns
        .flatMap((t) => (t.decision.rationale || "").split(";"))
        .map((s) => s.trim())
        .filter((r) => r.length > 0 && !NO_SYMPTOM_RATIONALES.has(r)),
    ),
  );

  const showToast = useCallback(
    (message: string, kind: "success" | "error") => {
      const id = toastIdRef.current++;
      setToasts((prev) => [...prev, { id, message, kind }]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 3500);
    },
    [],
  );

  const handleMicClick = async () => {
    if (!recording) {
      await startListening();
    } else {
      await stopAndSend();
    }
  };

  const handleEscalate = () => {
    showToast("Escalado a profesional de salud (demo)", "success");
  };

  const handleContinue = async () => {
    try {
      await startListening();
      showToast("Monitoreo continuado — escuchando", "success");
    } catch {
      showToast("No se pudo activar el micrófono", "error");
    }
  };

  const handleFollowUp = async () => {
    try {
      await handleMicClick();
    } catch {
      showToast("No se pudo procesar la pregunta de seguimiento", "error");
    }
  };

  const handleReport = async () => {
    try {
      const result = await postSummary(callId, DEFAULT_PACIENTE_ID);
      setSummary(result);
      showToast("Reporte generado", "success");
    } catch {
      showToast("No se pudo generar el reporte", "error");
    }
  };

  return (
    <div className="grid h-screen grid-cols-[300px_1fr_340px] gap-4 bg-gradient-to-br from-slate-50 via-blue-50 to-teal-50 p-4">
      <aside className="flex flex-col gap-4 overflow-y-auto rounded-xl border-t-4 border-clinical-blue bg-white/80 p-4 shadow-sm backdrop-blur-sm">
        <div className="shrink-0">
          <PatientCard patient={patient} />
        </div>
        <div className="shrink-0">
          <RecoveryStatus decision={decision} symptoms={symptoms} />
        </div>
      </aside>

      <main className="flex flex-col items-center gap-4 rounded-xl border-t-4 border-clinical-green bg-white/80 p-4 shadow-sm backdrop-blur-sm">
        <div className="shrink-0">
          <VoiceVisualizer state={state} />
        </div>
        <motion.button
          whileTap={{ scale: 0.95 }}
          onClick={handleMicClick}
          className="shrink-0 rounded-full bg-clinical-blue px-6 py-2 font-medium text-white shadow-md transition-shadow hover:shadow-lg"
        >
          {recording ? "Detener y enviar" : "Hablar"}
        </motion.button>
        <TranscriptViewer turns={turns} />
      </main>

      <aside className="flex flex-col gap-4 overflow-y-auto rounded-xl border-t-4 border-clinical-amber bg-white/80 p-4 shadow-sm backdrop-blur-sm">
        <div className="shrink-0">
          <RiskAssessment decision={decision} />
        </div>
        <div className="shrink-0">
          <AgentTimeline turns={turns} />
        </div>
        <div className="shrink-0">
          <EvidencePanel retrieval={retrieval} />
        </div>
        <div className="shrink-0">
          <ActionButtons
            escalationRequired={decision?.label === "rojo"}
            onEscalate={handleEscalate}
            onContinue={handleContinue}
            onFollowUp={handleFollowUp}
            onReport={handleReport}
          />
        </div>
        <AnimatePresence>
          {summary && (
            <div className="shrink-0">
              <CallSummaryCard summary={summary} />
            </div>
          )}
        </AnimatePresence>
      </aside>

      <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 12, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              className={`pointer-events-auto rounded-lg px-4 py-2 text-sm font-medium text-white shadow-lg ${
                t.kind === "success" ? "bg-clinical-green" : "bg-clinical-red"
              }`}
            >
              {t.message}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
