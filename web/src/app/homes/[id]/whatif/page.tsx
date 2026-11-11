import { Suspense } from "react";
import WhatIfClient from "./whatif-client";

export default function WhatIfPage() {
  return (
    <Suspense fallback={<div className="loading-panel">Preparing your what-if estimate…</div>}>
      <WhatIfClient />
    </Suspense>
  );
}
