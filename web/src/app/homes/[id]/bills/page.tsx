import { Suspense } from "react";
import BillsClient from "./bills-client";

export default function BillsPage() {
  return (
    <Suspense fallback={<div className="loading-panel">Loading your bills…</div>}>
      <BillsClient />
    </Suspense>
  );
}
