// frontend-app/src/components/EvidencePanel.tsx
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import type { RetrievalItem } from "../types";

function sourceHref(source: string): string {
  return `/api/source/${source
    .split("/")
    .map((part) => encodeURIComponent(part))
    .join("/")}`;
}

export function EvidencePanel({ retrieval }: { retrieval: RetrievalItem[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Fuentes utilizadas</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {retrieval.length === 0 ? (
          <p className="text-sm text-slate-500">Sin fuentes consultadas.</p>
        ) : (
          retrieval.map((r, i) => (
            <a
              key={i}
              href={sourceHref(r.source)}
              target="_blank"
              rel="noreferrer"
              title={`score: ${r.score.toFixed(2)}`}
              className="block w-full break-words rounded-lg border border-clinical-blue/20 bg-clinical-blue/5 px-3 py-2 text-xs text-clinical-blue underline-offset-2 transition-colors hover:bg-clinical-blue/10 hover:underline"
            >
              {r.source}
            </a>
          ))
        )}
      </CardContent>
    </Card>
  );
}
