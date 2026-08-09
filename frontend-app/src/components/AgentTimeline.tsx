// frontend-app/src/components/AgentTimeline.tsx
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import type { TimelineTurn } from "../types";

export function AgentTimeline({ turns }: { turns: TimelineTurn[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Actividad del agente</CardTitle>
      </CardHeader>
      <CardContent>
        {turns.length === 0 ? (
          <p className="text-sm text-slate-500">Sin actividad aún.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {turns.map((t, i) => (
              <li key={i} className="flex items-start gap-2">
                <span>✓</span>
                <span>
                  Turno {i + 1}: clasificado como{" "}
                  <span className="font-medium">{t.decision.label}</span>
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
