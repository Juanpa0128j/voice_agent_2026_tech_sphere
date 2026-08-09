// frontend-app/src/hooks/useVoiceCall.ts
import { useCallback, useRef, useState } from "react";
import { postAssist, postStt, postTts } from "../api";
import type { AgentState } from "../components/VoiceVisualizer";
import type {
  Decision,
  PatientContext,
  RetrievalItem,
  TimelineTurn,
} from "../types";

export function useVoiceCall(pacienteId: string) {
  const [state, setState] = useState<AgentState>("waiting");
  const [turns, setTurns] = useState<TimelineTurn[]>([]);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [patient, setPatient] = useState<PatientContext | null>(null);
  const [retrieval, setRetrieval] = useState<RetrievalItem[]>([]);
  const callIdRef = useRef(crypto.randomUUID());
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startListening = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);
    chunksRef.current = [];
    recorder.ondataavailable = (e) => chunksRef.current.push(e.data);
    recorder.start();
    mediaRecorderRef.current = recorder;
    setState("listening");
  }, []);

  const stopAndSend = useCallback(async () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder) return;

    setState("processing");
    const stopped = new Promise<Blob>((resolve) => {
      recorder.onstop = () =>
        resolve(new Blob(chunksRef.current, { type: "audio/webm" }));
    });
    recorder.stop();
    recorder.stream.getTracks().forEach((t) => t.stop());
    const audioBlob = await stopped;

    const { text } = await postStt(audioBlob);

    const result = await postAssist({
      transcript: text,
      call_id: callIdRef.current,
      paciente_id: pacienteId,
    });

    setTurns((prev) => [
      ...prev,
      {
        transcript: result.transcript,
        response: result.response,
        decision: result.decision,
      },
    ]);
    setDecision(result.decision);
    setPatient(result.patient);
    setRetrieval(result.retrieval);
    setState(result.decision.label === "rojo" ? "escalation" : "speaking");

    try {
      const audio = await postTts(result.response);
      const url = URL.createObjectURL(audio);
      const player = new Audio(url);
      player.onended = () =>
        setState(result.decision.label === "rojo" ? "escalation" : "waiting");
      await player.play();
    } catch {
      setState(result.decision.label === "rojo" ? "escalation" : "waiting");
    }
  }, [pacienteId]);

  return {
    state,
    turns,
    decision,
    patient,
    retrieval,
    startListening,
    stopAndSend,
    callId: callIdRef.current,
  };
}
