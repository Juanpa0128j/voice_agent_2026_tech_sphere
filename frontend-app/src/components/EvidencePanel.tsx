// frontend-app/src/components/EvidencePanel.tsx
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import type { RetrievalItem } from "../types";

export function EvidencePanel({ retrieval }: { retrieval: RetrievalItem[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Fuentes utilizadas</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-1">
        {retrieval.length === 0 ? (
          <p className="text-sm text-slate-500">Sin fuentes consultadas.</p>
        ) : (
          retrieval.map((r, i) => (
            <Badge
              key={i}
              variant="outline"
              title={`score: ${r.score.toFixed(2)}`}
            >
              {r.source}
            </Badge>
          ))
        )}
      </CardContent>
    </Card>
  );
}
