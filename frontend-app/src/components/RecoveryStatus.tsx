// frontend-app/src/components/RecoveryStatus.tsx
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Progress } from "./ui/progress";
import type { Decision } from "../types";

const LABEL_TEXT: Record<Decision["label"], string> = {
  verde: "Estable",
  amarillo: "En observación",
  rojo: "En riesgo",
};

const LABEL_VARIANT: Record<
  Decision["label"],
  "default" | "secondary" | "destructive"
> = {
  verde: "default",
  amarillo: "secondary",
  rojo: "destructive",
};

export function RecoveryStatus({
  decision,
  symptoms,
}: {
  decision: Decision | null;
  symptoms: string[];
}) {
  const label = decision?.label ?? "verde";
  const score = decision?.score ?? 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Estado de recuperación</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <Badge variant={LABEL_VARIANT[label]}>{LABEL_TEXT[label]}</Badge>
        <div>
          <p className="mb-1 text-xs text-slate-500">Severidad</p>
          <Progress value={Math.min(100, Math.max(0, score * 10))} />
        </div>
        <div>
          <p className="mb-1 text-xs text-slate-500">Síntomas detectados</p>
          <div className="flex flex-wrap gap-1">
            {symptoms.length === 0 ? (
              <span className="text-slate-400">Ninguno reportado aún</span>
            ) : (
              symptoms.map((s) => (
                <Badge key={s} variant="outline">
                  {s}
                </Badge>
              ))
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
