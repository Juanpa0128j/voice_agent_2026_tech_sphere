// frontend-app/src/components/VoiceVisualizer.tsx
import { motion } from "framer-motion";

export type AgentState =
  "listening" | "processing" | "speaking" | "waiting" | "escalation";

const STATE_LABEL: Record<AgentState, string> = {
  listening: "Escuchando",
  processing: "Procesando",
  speaking: "Hablando",
  waiting: "Esperando",
  escalation: "Escalamiento requerido",
};

const STATE_COLOR: Record<AgentState, string> = {
  listening: "bg-clinical-blue",
  processing: "bg-slate-400",
  speaking: "bg-clinical-green",
  waiting: "bg-slate-300",
  escalation: "bg-clinical-red",
};

export function VoiceVisualizer({ state }: { state: AgentState }) {
  const pulsing = state === "listening" || state === "speaking";

  return (
    <div className="flex flex-col items-center gap-3 py-8">
      <motion.div
        className={`h-28 w-28 rounded-full ${STATE_COLOR[state]}`}
        animate={pulsing ? { scale: [1, 1.15, 1] } : { scale: 1 }}
        transition={
          pulsing ? { duration: 1.2, repeat: Infinity, ease: "easeInOut" } : {}
        }
      />
      <p className="text-sm font-medium text-slate-600">{STATE_LABEL[state]}</p>
    </div>
  );
}
