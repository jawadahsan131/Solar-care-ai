import { Suspense } from "react";
import { redirect } from "next/navigation";
import AddAppliancesClient from "./add-client";

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export default async function AddAppliancesPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  return (
    <Suspense fallback={<div className="loading-panel">Loading appliance tools…</div>}>
      <AddAppliancesPageContent params={params} />
    </Suspense>
  );
}

async function AddAppliancesPageContent({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  if (!UUID_PATTERN.test(id)) redirect("/dashboard");
  return <AddAppliancesClient homeId={id} />;
}
