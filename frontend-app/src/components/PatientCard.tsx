// frontend-app/src/components/PatientCard.tsx
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import type { PatientContext } from "../types";

export function PatientCard({ patient }: { patient: PatientContext | null }) {
  if (!patient) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Paciente</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-500">
          Sin datos de paciente para esta llamada.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{patient.nombre || "Paciente sin nombre"}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <p>
          <span className="font-medium">Procedimiento:</span>{" "}
          {patient.procedimiento}
        </p>
        <p>
          <span className="font-medium">Día postoperatorio:</span>{" "}
          {patient.dia_postoperatorio}
        </p>
        <p>
          <span className="font-medium">EPS:</span> {patient.eps || "—"}
        </p>
        <div className="flex flex-wrap gap-1 pt-1">
          {patient.comorbilidades.length === 0 ? (
            <Badge variant="secondary">Sin comorbilidades</Badge>
          ) : (
            patient.comorbilidades.map((c) => (
              <Badge key={c} variant="secondary">
                {c}
              </Badge>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}
