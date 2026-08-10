// frontend-app/src/hooks/useVoiceCall.ts
import { useCallback, useEffect, useRef, useState } from "react";
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
  const [muted, setMuted] = useState(false);
  const callIdRef = useRef(crypto.randomUUID());
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const mutedRef = useRef(false);

  const toggleMute = useCallback(() => {
    setMuted((prev) => {
      const next = !prev;
      mutedRef.current = next;
      if (next) {
        // Pause the system: stop any playing agent audio and any active
        // recording, without losing whatever was already captured.
        if (currentAudioRef.current) {
          currentAudioRef.current.pause();
        }
        const recorder = mediaRecorderRef.current;
        if (recorder && recorder.state !== "inactive") {
          recorder.stream.getTracks().forEach((t) => t.stop());
        }
        setState("waiting");
      }
      return next;
    });
  }, []);

  const startListening = useCallback(async () => {
    if (mutedRef.current) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => chunksRef.current.push(e.data);
      recorder.start();
      mediaRecorderRef.current = recorder;
      setState("listening");
    } catch {
      setState("waiting");
    }
  }, []);

  const stopAndSend = useCallback(async () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder) return;

    setState("processing");
    try {
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

      if (mutedRef.current) {
        setState("waiting");
        return;
      }
      setState(result.decision.label === "rojo" ? "escalation" : "speaking");

      try {
        const audio = await postTts(result.response);
        const url = URL.createObjectURL(audio);
        const player = new Audio(url);
        currentAudioRef.current = player;
        player.onended = () =>
          setState(result.decision.label === "rojo" ? "escalation" : "waiting");
        await player.play();
      } catch {
        setState(result.decision.label === "rojo" ? "escalation" : "waiting");
      }
    } catch {
      setState("waiting");
    }
  }, [pacienteId]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setState("speaking");
        const result = await postAssist({
          transcript: "",
          call_id: callIdRef.current,
          paciente_id: pacienteId,
          greeting: true,
        });
        if (cancelled) return;

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

        if (mutedRef.current) {
          setState("waiting");
          return;
        }

        try {
          const audio = await postTts(result.response);
          const url = URL.createObjectURL(audio);
          const player = new Audio(url);
          currentAudioRef.current = player;
          player.onended = () => {
            if (!cancelled) setState("waiting");
          };
          await player.play();
        } catch {
          if (!cancelled) setState("waiting");
        }
      } catch {
        if (!cancelled) setState("waiting");
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    state,
    turns,
    decision,
    patient,
    retrieval,
    muted,
    toggleMute,
    startListening,
    stopAndSend,
    callId: callIdRef.current,
  };
}
