import fs from "fs";
import path from "path";
import Link from "next/link";

function readJson(filePath: string): Record<string, unknown> | null {
  try {
    const text = fs.readFileSync(filePath, "utf8");
    return JSON.parse(text) as Record<string, unknown>;
  } catch {
    return null;
  }
}

export default function AboutModelsPage() {
  const rootDir = path.resolve(process.cwd(), "..");
  const modelsDir = path.join(rootDir, "models");
  const docsDir = path.join(rootDir, "docs");
  const demandMeta = readJson(path.join(modelsDir, "demand_features.json"));
  const yoloClasses = readJson(path.join(modelsDir, "yolo_classes.json"));
  const weightsPresent = fs.existsSync(path.join(modelsDir, "best.pt"));
  const demandSynthetic = Boolean(demandMeta?.synthetic);
  const demandLabel = typeof demandMeta?.data_label === "string"
    ? demandMeta.data_label
    : typeof demandMeta?.label === "string"
      ? demandMeta.label
      : "unknown";

  const cards = [
    {
      title: "Detector",
      value: weightsPresent ? "YOLO weights present" : "Weights not trained yet",
      detail: `Backend: ${process.env.NEXT_PUBLIC_DETECT_BACKEND ?? "vlm"} · ${yoloClasses && Array.isArray(yoloClasses) ? yoloClasses.length : 0} classes loaded`,
    },
    {
      title: "Demand model",
      value: demandMeta ? (demandSynthetic ? "Synthetic data" : "Observed data") : "No model metadata",
      detail: `Label: ${demandLabel} · ${typeof demandMeta?.n_days === "number" ? `${demandMeta.n_days} days` : "n/a"}`,
    },
    {
      title: "Evaluation docs",
      value: fs.existsSync(path.join(docsDir, "yolo_eval.md")) && fs.existsSync(path.join(docsDir, "demand_eval.md")) ? "Documents available" : "Need evidence docs",
      detail: "Model claims should match the docs in this folder.",
    },
  ];

  return (
    <main className="models-page">
      <header className="models-header">
        <div>
          <p className="eyebrow">MODEL TRANSPARENCY</p>
          <h1>About the models behind the estimate</h1>
        </div>
        <Link className="button button-quiet" href="/dashboard">Open Today page</Link>
      </header>

      {demandSynthetic && (
        <div className="synthetic-badge">SYNTHETIC - not real accuracy</div>
      )}

      <section className="model-grid" aria-label="Model transparency cards">
        {cards.map((card) => (
          <article className="model-card" key={card.title}>
            <p className="eyebrow subtle">{card.title}</p>
            <h2>{card.value}</h2>
            <p>{card.detail}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
