// frontend-app/src/components/ActionButtons.tsx
import { Button } from "./ui/button";

export function ActionButtons({
  onEndCall,
  onReport,
  escalationRequired,
  ended,
}: {
  onEndCall: () => void;
  onReport: () => void;
  escalationRequired: boolean;
  ended: boolean;
}) {
  return (
    <div className="flex flex-col gap-2">
      {escalationRequired && (
        <div className="rounded-lg bg-clinical-red/10 px-3 py-2 text-sm font-medium text-clinical-red ring-1 ring-clinical-red/30">
          Alerta enviada automáticamente a profesional de salud
        </div>
      )}
      <Button variant="destructive" onClick={onEndCall} disabled={ended}>
        {ended ? "Llamada finalizada" : "Finalizar llamada"}
      </Button>
      <Button variant="secondary" onClick={onReport}>
        Generar reporte del paciente
      </Button>
    </div>
  );
}
