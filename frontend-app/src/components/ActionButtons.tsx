// frontend-app/src/components/ActionButtons.tsx
import { Button } from "./ui/button";

export function ActionButtons({
  onEscalate,
  onContinue,
  onFollowUp,
  onReport,
  escalationRequired,
}: {
  onEscalate: () => void;
  onContinue: () => void;
  onFollowUp: () => void;
  onReport: () => void;
  escalationRequired: boolean;
}) {
  return (
    <div className="flex flex-col gap-2">
      <Button
        variant={escalationRequired ? "destructive" : "outline"}
        onClick={onEscalate}
      >
        Escalar a profesional de salud
      </Button>
      <Button variant="secondary" onClick={onContinue}>
        Continuar monitoreo
      </Button>
      <Button variant="secondary" onClick={onFollowUp}>
        Hacer pregunta de seguimiento
      </Button>
      <Button variant="secondary" onClick={onReport}>
        Generar reporte del paciente
      </Button>
    </div>
  );
}
