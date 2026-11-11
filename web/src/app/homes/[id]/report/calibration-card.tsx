"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { apiFetch } from "@/lib/api";

type CalibrationProposal = {
  appliance_id: string | null;
  type: string;
  field: "hours_per_day";
  current: number;
  suggested: number;
  reason: string;
};

type Calibration = {
  estimated_monthly_kwh: number;
  bill_monthly_kwh: number | null;
  ratio: number | null;
  band: string;
  reasons: string[];
  proposals: CalibrationProposal[];
};

export default function CalibrationCard() {
  const { id } = useParams<{ id: string }>();
  const [calibration, setCalibration] = useState<Calibration | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [notice, setNotice] = useState("");

  const loadCalibration = useCallback(async () => {
    try {
      const result = await apiFetch<Calibration>(`/homes/${id}/calibration`);
      setCalibration(result);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not load bill calibration.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void Promise.resolve().then(loadCalibration);
  }, [loadCalibration]);

  async function accept(proposal: CalibrationProposal) {
    if (!proposal.appliance_id) return;
    setBusyId(proposal.appliance_id);
    setErrorMessage("");
    setNotice("");
    try {
      await apiFetch(`/appliances/${proposal.appliance_id}`, {
        method: "PATCH",
        body: JSON.stringify({ hours_per_day: proposal.suggested }),
      });
      setNotice("Suggestion applied and marked as user-verified.");
      await loadCalibration();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not apply this suggestion.");
    } finally {
      setBusyId("");
    }
  }

  function reject(proposal: CalibrationProposal) {
    if (!calibration) return;
    setCalibration({
      ...calibration,
      proposals: calibration.proposals.filter((item) => item !== proposal),
    });
  }

  return (
    <section className="report-panel calibration-panel" aria-labelledby="calibration-heading">
      <div className="panel-heading">
        <div><p className="eyebrow">BILL CHECK</p><h2 id="calibration-heading">Compare estimate with your bill</h2></div>
      </div>
      {loading ? <p className="muted">Checking saved bills…</p> : null}
      {errorMessage && <p className="inline-error" role="alert">{errorMessage}</p>}
      {notice && <p className="inline-notice" role="status">{notice}</p>}
      {calibration && (
        <>
          <div className="calibration-summary">
            <p>Your appliance list estimates <strong>{calibration.estimated_monthly_kwh.toFixed(1)} kWh/month</strong>.</p>
            <p>
              {calibration.bill_monthly_kwh === null
                ? "Add a bill to compare real monthly usage."
                : `Your latest bill reports ${calibration.bill_monthly_kwh.toFixed(1)} kWh.`}
            </p>
            {calibration.ratio !== null && <span className="calibration-band">{calibration.band}</span>}
          </div>
          {calibration.reasons.length > 0 && (
            <p className="muted calibration-reasons">Things to review: {calibration.reasons.join("; ")}.</p>
          )}
          {calibration.proposals.length > 0 && (
            <div className="calibration-proposals">
              <h3>Optional appliance-hour suggestions</h3>
              {calibration.proposals.map((proposal, index) => (
                <div className="calibration-proposal" key={`${proposal.appliance_id}-${proposal.type}-${index}`}>
                  <p>
                    Increase {proposal.type.replaceAll("_", " ")} from {proposal.current} to {proposal.suggested} hours/day?
                    <small>{proposal.reason} This is only a proposal; your appliance list will not change unless you accept.</small>
                  </p>
                  <div>
                    <button
                      className="button button-primary"
                      disabled={!proposal.appliance_id || busyId === proposal.appliance_id}
                      onClick={() => void accept(proposal)}
                      type="button"
                    >{busyId === proposal.appliance_id ? "Applying…" : "Accept"}</button>
                    <button className="button button-quiet" onClick={() => reject(proposal)} type="button">Reject</button>
                  </div>
                </div>
              ))}
            </div>
          )}
          <Link className="text-link" href={`/homes/${id}/bills`}>Manage bills and review history</Link>
        </>
      )}
    </section>
  );
}
