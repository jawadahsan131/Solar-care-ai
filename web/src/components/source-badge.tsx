import type { SourceTag } from "@/lib/types";

const sourceLabels: Record<SourceTag, string> = {
  label: "Read from label",
  catalog: "Matched in catalog",
  guess: "Typical value · confirm",
  user: "You entered",
};

export default function SourceBadge({
  source,
  confidence,
}: {
  source: SourceTag;
  confidence?: number | null;
}) {
  return (
    <span className={`source-badge source-${source}`}>
      {sourceLabels[source]}
      {confidence !== null && confidence !== undefined && (
        <small>{Math.round(confidence * 100)}%</small>
      )}
    </span>
  );
}
