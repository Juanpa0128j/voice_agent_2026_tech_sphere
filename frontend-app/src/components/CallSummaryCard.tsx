// frontend-app/src/components/CallSummaryCard.tsx
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import type { CallSummary } from "../types";

const LABEL_VARIANT: Record<string, "default" | "secondary" | "destructive"> = {
  verde: "default",
  amarillo: "secondary",
  rojo: "destructive",
};

function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString("es-CO", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

export function CallSummaryCard({ summary }: { summary: CallSummary }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      <Card className="border-clinical-blue/30">
        <CardHeader>
          <CardTitle>Resumen de la llamada</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          {(summary.nombre || summary.procedimiento) && (
            <div>
              <p className="font-medium">
                {summary.nombre || "Paciente sin nombre"}
              </p>
              {summary.procedimiento && (
                <p className="text-slate-600">
                  {summary.procedimiento}
                  {summary.dia_postoperatorio
                    ? ` · día postoperatorio ${summary.dia_postoperatorio}`
                    : ""}
                </p>
              )}
            </div>
          )}

          <div className="flex items-center gap-2">
            <span className="text-slate-500">Decisión final:</span>
            <Badge variant={LABEL_VARIANT[summary.decision] ?? "secondary"}>
              {summary.decision.toUpperCase()}
            </Badge>
            {summary.alerta_enviada && (
              <Badge variant="destructive">Alerta enviada</Badge>
            )}
          </div>

          <div>
            <p className="mb-1 text-xs font-medium uppercase text-slate-500">
              Síntomas reportados
            </p>
            {summary.sintomas_reportados.length === 0 ? (
              <p className="text-slate-400">Ninguno</p>
            ) : (
              <div className="flex flex-wrap gap-1">
                {summary.sintomas_reportados.map((s) => (
                  <Badge key={s} variant="outline">
                    {s}
                  </Badge>
                ))}
              </div>
            )}
          </div>

          {summary.proximos_pasos.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-medium uppercase text-slate-500">
                Próximos pasos
              </p>
              <ul className="list-inside list-disc space-y-0.5 text-slate-700">
                {summary.proximos_pasos.map((p, i) => (
                  <li key={i}>{p}</li>
                ))}
              </ul>
            </div>
          )}

          {summary.fuentes.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-medium uppercase text-slate-500">
                Fuentes citadas
              </p>
              <ul className="space-y-0.5 text-slate-700">
                {summary.fuentes.map((f) => (
                  <li key={f.id} className="break-words">
                    {f.id}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <p className="pt-1 text-xs text-slate-400">
            {formatTimestamp(summary.timestamp)}
            {typeof summary.mensajes === "number"
              ? ` · ${summary.mensajes} mensajes`
              : ""}
          </p>
        </CardContent>
      </Card>
    </motion.div>
  );
}
