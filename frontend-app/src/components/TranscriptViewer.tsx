// frontend-app/src/components/TranscriptViewer.tsx
import { motion } from "framer-motion";
import type { TimelineTurn } from "../types";

export function TranscriptViewer({ turns }: { turns: TimelineTurn[] }) {
  return (
    <div className="flex max-h-80 w-full flex-col gap-3 overflow-y-auto p-2">
      {turns.length === 0 && (
        <p className="text-sm text-slate-400">
          La conversación aparecerá aquí.
        </p>
      )}
      {turns.map((turn, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="space-y-1"
        >
          {turn.transcript && (
            <div className="rounded-lg bg-slate-100 px-3 py-2 text-sm">
              <span className="font-medium text-slate-500">Paciente:</span>{" "}
              {turn.transcript}
            </div>
          )}
          <div className="rounded-lg bg-gradient-to-r from-blue-50 to-teal-50 px-3 py-2 text-sm">
            <span className="font-medium text-blue-600">Agente:</span>{" "}
            {turn.response}
          </div>
        </motion.div>
      ))}
    </div>
  );
}
