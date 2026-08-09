// frontend-app/src/types.ts
export interface Decision {
  label: "verde" | "amarillo" | "rojo";
  score: number;
  rationale: string;
  alert: boolean;
  action: "respond" | "warn" | "alert";
}

export interface RetrievalItem {
  source: string;
  score: number;
  text?: string;
}

export interface PatientContext {
  paciente_id: string;
  nombre: string;
  procedimiento: string;
  dia_postoperatorio: number;
  comorbilidades: string[];
  eps: string;
}

export interface AssistResponse {
  call_id: string;
  transcript: string;
  response: string;
  decision: Decision;
  retrieval: RetrievalItem[];
  patient: PatientContext | null;
}

export interface TimelineTurn {
  transcript: string;
  response: string;
  decision: Decision;
}

export interface TimelineResponse {
  call_id: string;
  turns: TimelineTurn[];
}
