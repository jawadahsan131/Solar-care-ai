import { Suspense } from "react";
import ReportClient from "./report-client";

export default function SizingReportPage() {
  return (
    <Suspense fallback={<div className="loading-panel">Preparing your solar report…</div>}>
      <ReportClient />
    </Suspense>
  );
}
