// frontend-app/src/App.tsx
import { PatientCard } from "./components/PatientCard";
import { RecoveryStatus } from "./components/RecoveryStatus";
import { VoiceVisualizer } from "./components/VoiceVisualizer";
import { TranscriptViewer } from "./components/TranscriptViewer";
import { RiskAssessment } from "./components/RiskAssessment";
import { AgentTimeline } from "./components/AgentTimeline";
import { EvidencePanel } from "./components/EvidencePanel";
import { ActionButtons } from "./components/ActionButtons";
import { useVoiceCall } from "./hooks/useVoiceCall";
import { postSummary } from "./api";

const DEFAULT_PACIENTE_ID = "P001";

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

  const symptoms = Array.from(
    new Set(turns.map((t) => t.decision.rationale).filter(Boolean)),
  );

  const handleMicClick = async () => {
    if (!recording) {
      await startListening();
    } else {
      await stopAndSend();
    }
  };

  return (
    <div className="grid h-screen grid-cols-[300px_1fr_340px] gap-4 bg-slate-50 p-4">
      <aside className="flex flex-col gap-4 overflow-y-auto rounded-xl bg-white p-4 shadow-sm">
        <PatientCard patient={patient} />
        <RecoveryStatus decision={decision} symptoms={symptoms} />
      </aside>

      <main className="flex flex-col items-center gap-4 rounded-xl bg-white p-4 shadow-sm">
        <VoiceVisualizer state={state} />
        <button
          onClick={handleMicClick}
          className="rounded-full bg-clinical-blue px-6 py-2 text-white"
        >
          {recording ? "Detener y enviar" : "Hablar"}
        </button>
        <TranscriptViewer turns={turns} />
      </main>

      <aside className="flex flex-col gap-4 overflow-y-auto rounded-xl bg-white p-4 shadow-sm">
        <RiskAssessment decision={decision} />
        <AgentTimeline turns={turns} />
        <EvidencePanel retrieval={retrieval} />
        <ActionButtons
          escalationRequired={decision?.label === "rojo"}
          onEscalate={() => alert("Escalado a profesional de salud (demo)")}
          onContinue={() => startListening()}
          onFollowUp={handleMicClick}
          onReport={() =>
            postSummary(callId).then((s) => console.log("summary", s))
          }
        />
      </aside>
    </div>
  );
}
