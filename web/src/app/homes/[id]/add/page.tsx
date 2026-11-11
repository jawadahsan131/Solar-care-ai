import { Suspense } from "react";
import AddAppliancesClient from "./add-client";

export default function AddAppliancesPage() {
  return (
    <Suspense fallback={<div className="loading-panel">Loading appliance tools…</div>}>
      <AddAppliancesClient />
    </Suspense>
  );
}
