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
// Barge-in: how loud and how long the mic must read while the agent is
// speaking before we treat it as the patient interrupting.
const BARGE_IN_RMS = 0.03;
const BARGE_IN_MS = 300;

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
  onerror: ((event: any) => void) | null; // eslint-disable-line @typescript-eslint/no-explicit-any
  onend: (() => void) | null;
}

function getSpeechRecognitionCtor(): (new () => SpeechRecognitionLike) | null {
  const w = window as unknown as Record<string, unknown>;
  const ctor = (w.SpeechRecognition || w.webkitSpeechRecognition) as
    (new () => SpeechRecognitionLike) | undefined;
  return ctor ?? null;
}

type Phase = "idle" | "listening" | "processing" | "speaking";

export function useVoiceCall(pacienteId: string) {
  const [state, setState] = useState<AgentState>("waiting");
  const [turns, setTurns] = useState<TimelineTurn[]>([]);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [patient, setPatient] = useState<PatientContext | null>(null);
  const [retrieval, setRetrieval] = useState<RetrievalItem[]>([]);
  const [muted, setMuted] = useState(false);
  const [liveCaption, setLiveCaption] = useState("");
  const callIdRef = useRef(crypto.randomUUID());

  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

  const mutedRef = useRef(false);
  const endedRef = useRef(false);
  const busyRef = useRef(false); // true while sending/awaiting a turn (STT->assist->TTS)
  const phaseRef = useRef<Phase>("idle");
  const spokeOnceRef = useRef(false);
  const rafRef = useRef<number | null>(null);

  const startListeningRef = useRef<() => Promise<void>>(async () => {});
  const finishRecordingRef = useRef<() => void>(() => {});
  const bargeInRef = useRef<() => void>(() => {});

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

  const startLiveCaption = useCallback(() => {
    if (recognitionRef.current) return; // already running
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
        // Live caption is cosmetic only — never affects the real pipeline.
        // Common causes: browser lacks network access to the speech
        // service, or "es-CO" isn't recognized. Just stop trying for
        // this turn instead of retrying forever.
        recognitionRef.current = null;
      };
      recognition.onend = () => {
        recognitionRef.current = null;
      };
      recognition.start();
      recognitionRef.current = recognition;
    } catch {
      // Some browsers throw synchronously — live caption is best-effort.
    }
  }, []);

  const ensureStream = useCallback(async (): Promise<MediaStream> => {
    if (streamRef.current) return streamRef.current;
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    streamRef.current = stream;
    return stream;
  }, []);

  const ensureAnalyser = useCallback((stream: MediaStream): AnalyserNode => {
    if (analyserRef.current) return analyserRef.current;
    if (!audioCtxRef.current) {
      audioCtxRef.current = new (
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext })
          .webkitAudioContext
      )();
    }
    const src = audioCtxRef.current.createMediaStreamSource(stream);
    const analyser = audioCtxRef.current.createAnalyser();
    analyser.fftSize = 2048;
    src.connect(analyser);
    analyserRef.current = analyser;
    return analyser;
  }, []);

  const releaseStream = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      try {
        recorder.stop();
      } catch {
        /* ignore */
      }
    }
    mediaRecorderRef.current = null;
    stopLiveCaption();
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    analyserRef.current = null;
    phaseRef.current = "idle";
  }, [stopLiveCaption]);

  const beginRecording = useCallback(
    (stream: MediaStream, opts: { discardFirstMs?: number } = {}) => {
      let recorder: MediaRecorder;
      try {
        recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      } catch {
        recorder = new MediaRecorder(stream);
      }
      const chunks: Blob[] = [];
      chunksRef.current = chunks;
      mediaRecorderRef.current = recorder;
      spokeOnceRef.current = Boolean(opts.discardFirstMs); // barge-in already proved speech

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size) chunks.push(e.data);
      };
      recorder.onstop = () => {
        if (mediaRecorderRef.current === recorder)
          mediaRecorderRef.current = null;
        stopLiveCaption();
        if (!spokeOnceRef.current || !chunks.length) {
          busyRef.current = false;
          phaseRef.current = "idle";
          if (!(mutedRef.current || endedRef.current))
            void startListeningRef.current();
          else setState("waiting");
          return;
        }
        const blob = new Blob(chunks, {
          type: recorder.mimeType || "audio/webm",
        });
        void (async () => {
          busyRef.current = true;
          phaseRef.current = "processing";
          setState("processing");
          try {
            const { text } = await postStt(blob);
            const trimmed = text.trim();
            if (!trimmed) {
              busyRef.current = false;
              phaseRef.current = "idle";
              if (!(mutedRef.current || endedRef.current))
                await startListeningRef.current();
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

            if (mutedRef.current || endedRef.current) {
              busyRef.current = false;
              phaseRef.current = "idle";
              setState("waiting");
              return;
            }

            setState(
              result.decision.label === "rojo" ? "escalation" : "speaking",
            );
            phaseRef.current = "speaking";

            try {
              const audio = await postTts(result.response);
              if (endedRef.current) {
                busyRef.current = false;
                phaseRef.current = "idle";
                setState("waiting");
                return;
              }
              const url = URL.createObjectURL(audio);
              const player = new Audio(url);
              currentAudioRef.current = player;
              player.onended = () => {
                busyRef.current = false;
                currentAudioRef.current = null;
                phaseRef.current = "idle";
                if (mutedRef.current || endedRef.current) {
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
              phaseRef.current = "idle";
              if (!(mutedRef.current || endedRef.current)) {
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
            phaseRef.current = "idle";
            if (!(mutedRef.current || endedRef.current)) {
              await startListeningRef.current();
            } else {
              setState("waiting");
            }
          }
        })();
      };
      recorder.start(250);
      phaseRef.current = "listening";
      setState("listening");
      startLiveCaption();
    },
    [pacienteId, startLiveCaption, stopLiveCaption],
  );

  const finishRecording = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
    }
  }, []);
  finishRecordingRef.current = finishRecording;

  const bargeIn = useCallback(() => {
    // Note: busyRef is intentionally NOT checked here — it's true for
    // the whole duration of the speaking phase by design, so gating on
    // it would make barge-in impossible during real TTS playback.
    if (mutedRef.current || endedRef.current) return;
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    const stream = streamRef.current;
    if (!stream) return;
    // The patient already proved they're speaking — start capturing now,
    // treating this exactly like a normal listening turn from here on.
    beginRecording(stream, { discardFirstMs: 1 });
  }, [beginRecording]);
  bargeInRef.current = bargeIn;

  // Single continuous monitor loop: drives both silence-detection while
  // listening AND barge-in detection while the agent is speaking. Runs
  // for the lifetime of the persistent mic stream.
  const runMonitor = useCallback(() => {
    const stream = streamRef.current;
    if (!stream || mutedRef.current || endedRef.current) {
      rafRef.current = null;
      return;
    }
    const analyser = ensureAnalyser(stream);
    const buf = new Float32Array(analyser.fftSize);
    let silentSince: number | null = null;
    let loudSince: number | null = null;
    let listenStartedAt = Date.now();

    const tick = () => {
      if (!streamRef.current || mutedRef.current || endedRef.current) {
        rafRef.current = null;
        return;
      }
      analyser.getFloatTimeDomainData(buf);
      let sum = 0;
      for (let i = 0; i < buf.length; i++) sum += buf[i] * buf[i];
      const rms = Math.sqrt(sum / buf.length);
      const now = Date.now();

      if (phaseRef.current === "listening") {
        if (rms > SILENCE_RMS) {
          spokeOnceRef.current = true;
          silentSince = null;
        } else if (spokeOnceRef.current) {
          if (silentSince === null) silentSince = now;
          if (now - silentSince > SILENCE_MS) {
            finishRecordingRef.current();
            rafRef.current = requestAnimationFrame(tick);
            return;
          }
        }
        if (now - listenStartedAt > MAX_RECORD_MS) {
          finishRecordingRef.current();
        }
      } else if (phaseRef.current === "speaking" && currentAudioRef.current) {
        // Only counts as barge-in once agent audio actually exists and is
        // playing — phaseRef flips to "speaking" as soon as we start
        // fetching TTS, well before there's anything to interrupt.
        if (rms > BARGE_IN_RMS) {
          if (loudSince === null) loudSince = now;
          if (now - loudSince > BARGE_IN_MS) {
            loudSince = null;
            bargeInRef.current();
            listenStartedAt = Date.now();
          }
        } else {
          loudSince = null;
        }
      } else {
        listenStartedAt = now;
      }

      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
  }, [ensureAnalyser]);

  const startListening = useCallback(async () => {
    if (mutedRef.current || busyRef.current || endedRef.current) return;
    try {
      const stream = await ensureStream();
      beginRecording(stream);
      if (rafRef.current === null) runMonitor();
    } catch {
      setState("waiting");
    }
  }, [beginRecording, ensureStream, runMonitor]);
  startListeningRef.current = startListening;

  const startSpeakingPhase = useCallback(async () => {
    // Called right before the greeting/agent audio starts playing, so the
    // monitor can watch for barge-in — needs the mic stream live already.
    try {
      const stream = await ensureStream();
      phaseRef.current = "speaking";
      if (rafRef.current === null) runMonitor();
      return stream;
    } catch {
      return null;
    }
  }, [ensureStream, runMonitor]);

  const toggleMute = useCallback(() => {
    setMuted((prev) => {
      const next = !prev;
      mutedRef.current = next;
      if (next) {
        // Mute the mic only — the agent keeps speaking if it already is.
        spokeOnceRef.current = false;
        const recorder = mediaRecorderRef.current;
        if (recorder && recorder.state !== "inactive") {
          // Discard whatever was captured so far rather than sending a
          // half-formed utterance the user explicitly muted mid-way.
          recorder.onstop = null;
          try {
            recorder.stop();
          } catch {
            /* ignore */
          }
          mediaRecorderRef.current = null;
        }
        if (phaseRef.current === "listening") {
          phaseRef.current = "idle";
          if (!busyRef.current) setState("waiting");
        }
        releaseStream();
      } else if (!busyRef.current) {
        phaseRef.current = "idle";
        void startListeningRef.current();
      }
      return next;
    });
  }, [releaseStream]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setState("speaking");
        await startSpeakingPhase();
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

        if (mutedRef.current || endedRef.current) {
          phaseRef.current = "idle";
          setState("waiting");
          return;
        }

        try {
          const audio = await postTts(result.response);
          if (cancelled || endedRef.current) {
            setState("waiting");
            return;
          }
          const url = URL.createObjectURL(audio);
          const player = new Audio(url);
          currentAudioRef.current = player;
          player.onended = () => {
            currentAudioRef.current = null;
            phaseRef.current = "idle";
            if (cancelled) return;
            if (mutedRef.current || endedRef.current) {
              setState("waiting");
              return;
            }
            void startListeningRef.current();
          };
          await player.play();
        } catch {
          phaseRef.current = "idle";
          if (!cancelled && !(mutedRef.current || endedRef.current)) {
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
      releaseStream();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const [ended, setEnded] = useState(false);

  const endCall = useCallback(() => {
    if (endedRef.current) return;
    endedRef.current = true;
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    releaseStream();
    setState("waiting");
    setEnded(true);
  }, [releaseStream]);

  return {
    state,
    turns,
    decision,
    patient,
    retrieval,
    muted,
    ended,
    toggleMute,
    liveCaption,
    startListening,
    endCall,
    callId: callIdRef.current,
  };
}
