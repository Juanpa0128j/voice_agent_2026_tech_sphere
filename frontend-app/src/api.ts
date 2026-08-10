// frontend-app/src/api.ts
import type { AssistResponse, CallSummary, TimelineResponse } from "./types";

async function jsonOrThrow<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    throw new Error(`Request failed: ${resp.status}`);
  }
  return resp.json() as Promise<T>;
}

export function postAssist(req: {
  transcript: string;
  call_id?: string;
  paciente_id?: string;
  greeting?: boolean;
}): Promise<AssistResponse> {
  return fetch("/api/assist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  }).then((r) => jsonOrThrow<AssistResponse>(r));
}

export function postStt(
  blob: Blob,
): Promise<{ text: string; language: string; duration_ms: number }> {
  const form = new FormData();
  form.append("file", blob, "audio.webm");
  return fetch("/api/stt", { method: "POST", body: form }).then((r) =>
    jsonOrThrow(r),
  );
}

export function postTts(text: string): Promise<Blob> {
  return fetch("/api/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  }).then((r) => {
    if (!r.ok) throw new Error(`TTS failed: ${r.status}`);
    return r.blob();
  });
}

export function getTimeline(callId: string): Promise<TimelineResponse> {
  return fetch(`/api/timeline/${encodeURIComponent(callId)}`).then((r) =>
    jsonOrThrow<TimelineResponse>(r),
  );
}

export function postSummary(
  callId: string,
  pacienteId?: string,
): Promise<CallSummary> {
  return fetch("/api/summary", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ call_id: callId, paciente_id: pacienteId }),
  }).then((r) => jsonOrThrow<CallSummary>(r));
}
