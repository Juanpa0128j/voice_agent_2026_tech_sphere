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

const SILENCE_RMS = 0.015;
const SILENCE_MS = 2200;
const MAX_RECORD_MS = 30000;

// Minimal ambient types for the non-standard SpeechRecognition API — used
// only for the on-screen live caption, never for the transcript sent to
// the backend (that always comes from /api/stt / Groq Whisper).
interface SpeechRecognitionLike extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  onresult: ((event: any) => void) | null; // eslint-disable-line @typescript-eslint/no-explicit-any
  onerror: (() => void) | null;
  onend: (() => void) | null;
}

function getSpeechRecognitionCtor(): (new () => SpeechRecognitionLike) | null {
  const w = window as unknown as Record<string, unknown>;
  const ctor = (w.SpeechRecognition || w.webkitSpeechRecognition) as
    (new () => SpeechRecognitionLike) | undefined;
  return ctor ?? null;
}

export function useVoiceCall(pacienteId: string) {
  const [state, setState] = useState<AgentState>("waiting");
  const [turns, setTurns] = useState<TimelineTurn[]>([]);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [patient, setPatient] = useState<PatientContext | null>(null);
  const [retrieval, setRetrieval] = useState<RetrievalItem[]>([]);
  const [muted, setMuted] = useState(false);
  const [liveCaption, setLiveCaption] = useState("");
  const callIdRef = useRef(crypto.randomUUID());
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const mutedRef = useRef(false);
  const busyRef = useRef(false);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

  const stopLiveCaption = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        /* ignore */
      }
      recognitionRef.current = null;
    }
    setLiveCaption("");
  }, []);

  const startLiveCaption = useCallback((stream: MediaStream) => {
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) return; // unsupported browser: no live caption, no error
    try {
      const recognition = new Ctor();
      recognition.lang = "es-CO";
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.onresult = (event) => {
        let text = "";
        for (let i = 0; i < event.results.length; i++) {
          text += event.results[i][0].transcript;
        }
        setLiveCaption(text);
      };
      recognition.onerror = () => {
        /* live caption is cosmetic only — swallow and keep recording */
      };
      recognition.onend = () => {
        recognitionRef.current = null;
      };
      recognition.start();
      recognitionRef.current = recognition;
    } catch {
      // Some browsers throw synchronously (e.g. no mic permission yet
      // for this API specifically) — live caption is best-effort only.
    }
    void stream; // SpeechRecognition uses its own mic access, not this stream
  }, []);

  // Forward declaration via ref so startListening (defined below) and the
  // post-turn auto-relisten logic can call each other without a circular
  // dependency in useCallback's dependency arrays.
  const startListeningRef = useRef<() => Promise<void>>(async () => {});

  const runTurn = useCallback(
    async (blob: Blob) => {
      busyRef.current = true;
      setState("processing");
      try {
        const { text } = await postStt(blob);
        const trimmed = text.trim();
        if (!trimmed) {
          busyRef.current = false;
          if (!mutedRef.current) await startListeningRef.current();
          else setState("waiting");
          return;
        }

        const result = await postAssist({
          transcript: trimmed,
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
          busyRef.current = false;
          setState("waiting");
          return;
        }

        setState(result.decision.label === "rojo" ? "escalation" : "speaking");

        try {
          const audio = await postTts(result.response);
          const url = URL.createObjectURL(audio);
          const player = new Audio(url);
          currentAudioRef.current = player;
          player.onended = () => {
            busyRef.current = false;
            currentAudioRef.current = null;
            if (mutedRef.current) {
              setState("waiting");
              return;
            }
            setState(
              result.decision.label === "rojo" ? "escalation" : "listening",
            );
            void startListeningRef.current();
          };
          await player.play();
        } catch {
          busyRef.current = false;
          if (!mutedRef.current) {
            setState(
              result.decision.label === "rojo" ? "escalation" : "listening",
            );
            await startListeningRef.current();
          } else {
            setState(
              result.decision.label === "rojo" ? "escalation" : "waiting",
            );
          }
        }
      } catch {
        busyRef.current = false;
        if (!mutedRef.current) {
          await startListeningRef.current();
        } else {
          setState("waiting");
        }
      }
    },
    [pacienteId],
  );

  const startListening = useCallback(async () => {
    if (mutedRef.current || busyRef.current) return;
    busyRef.current = true;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });
      let recorder: MediaRecorder;
      try {
        recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      } catch {
        recorder = new MediaRecorder(stream);
      }
      const chunks: Blob[] = [];
      chunksRef.current = chunks;
      mediaRecorderRef.current = recorder;
      let spokeOnce = false;
      setState("listening");
      startLiveCaption(stream);

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size) chunks.push(e.data);
      };
      recorder.onstop = () => {
        stopLiveCaption();
        stream.getTracks().forEach((t) => t.stop());
        if (!spokeOnce || !chunks.length) {
          busyRef.current = false;
          if (!mutedRef.current) void startListeningRef.current();
          else setState("waiting");
          return;
        }
        const blob = new Blob(chunks, {
          type: recorder.mimeType || "audio/webm",
        });
        void runTurn(blob);
      };
      recorder.start(250);

      try {
        if (!audioCtxRef.current) {
          audioCtxRef.current = new (
            window.AudioContext ||
            (window as unknown as { webkitAudioContext: typeof AudioContext })
              .webkitAudioContext
          )();
        }
        const audioCtx = audioCtxRef.current;
        const src = audioCtx.createMediaStreamSource(stream);
        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 2048;
        src.connect(analyser);
        const buf = new Float32Array(analyser.fftSize);
        let silentSince: number | null = null;
        const startedAt = Date.now();

        const check = () => {
          if (
            mediaRecorderRef.current !== recorder ||
            recorder.state === "inactive"
          ) {
            return;
          }
          analyser.getFloatTimeDomainData(buf);
          let sum = 0;
          for (let i = 0; i < buf.length; i++) sum += buf[i] * buf[i];
          const rms = Math.sqrt(sum / buf.length);
          const now = Date.now();
          if (rms > SILENCE_RMS) {
            spokeOnce = true;
            silentSince = null;
          } else if (spokeOnce) {
            if (silentSince === null) silentSince = now;
            if (now - silentSince > SILENCE_MS) {
              recorder.stop();
              return;
            }
          }
          if (now - startedAt > MAX_RECORD_MS) {
            recorder.stop();
            return;
          }
          requestAnimationFrame(check);
        };
        check();
      } catch {
        // No AnalyserNode support: fall back to a fixed recording window.
        setTimeout(() => {
          if (
            mediaRecorderRef.current === recorder &&
            recorder.state !== "inactive"
          ) {
            recorder.stop();
          }
        }, 6000);
      }
    } catch {
      busyRef.current = false;
      setState("waiting");
    }
  }, [runTurn, startLiveCaption, stopLiveCaption]);

  startListeningRef.current = startListening;

  const toggleMute = useCallback(() => {
    setMuted((prev) => {
      const next = !prev;
      mutedRef.current = next;
      if (next) {
        if (currentAudioRef.current) {
          currentAudioRef.current.pause();
        }
        const recorder = mediaRecorderRef.current;
        if (recorder && recorder.state !== "inactive") {
          recorder.stop();
        }
        stopLiveCaption();
        setState("waiting");
      } else if (!busyRef.current) {
        void startListeningRef.current();
      }
      return next;
    });
  }, [stopLiveCaption]);

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
            currentAudioRef.current = null;
            if (cancelled) return;
            if (mutedRef.current) {
              setState("waiting");
              return;
            }
            void startListeningRef.current();
          };
          await player.play();
        } catch {
          if (!cancelled && !mutedRef.current) {
            void startListeningRef.current();
          } else if (!cancelled) {
            setState("waiting");
          }
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
    liveCaption,
    startListening,
    callId: callIdRef.current,
  };
}
