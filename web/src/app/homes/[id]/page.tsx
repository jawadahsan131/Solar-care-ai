import { Suspense } from "react";
import AppliancesClient from "./appliances-client";

export default function HomeAppliancesPage() {
  return (
    <Suspense fallback={<div className="loading-panel">Loading your home…</div>}>
      <AppliancesClient />
    </Suspense>
  );
}
