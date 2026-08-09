// frontend-app/src/components/RiskAssessment.tsx
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import type { Decision } from "../types";

const RISK_TEXT: Record<Decision["label"], string> = {
  verde: "BAJO",
  amarillo: "MEDIO",
  rojo: "ALTO",
};

export function RiskAssessment({ decision }: { decision: Decision | null }) {
  if (!decision) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Evaluación clínica</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-500">
          Sin evaluación todavía.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Evaluación clínica</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <p>
          <span className="font-medium">Nivel de riesgo:</span>{" "}
          <Badge
            variant={decision.label === "rojo" ? "destructive" : "secondary"}
          >
            {RISK_TEXT[decision.label]}
          </Badge>
        </p>
        <p>
          <span className="font-medium">Confianza:</span>{" "}
          {Math.round(Math.min(1, decision.score / 10) * 100)}%
        </p>
        <p className="text-slate-600">{decision.rationale}</p>
      </CardContent>
    </Card>
  );
}
