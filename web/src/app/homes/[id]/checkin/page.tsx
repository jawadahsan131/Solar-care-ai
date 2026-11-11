import { Suspense } from "react";
import CheckinClient from "./checkin-client";

export default function CheckinPage() {
  return (
    <Suspense fallback={<div className="loading-panel">Loading check-in…</div>}>
      <CheckinClient />
    </Suspense>
  );
}
