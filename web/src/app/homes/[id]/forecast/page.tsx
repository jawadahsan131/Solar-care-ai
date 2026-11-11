import { Suspense } from "react";
import ForecastClient from "./forecast-client";

export default function ForecastPage() {
  return (
    <Suspense fallback={<div className="loading-panel">Loading the forecast…</div>}>
      <ForecastClient />
    </Suspense>
  );
}
