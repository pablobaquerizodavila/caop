import Link from "next/link";

import { type CaseSummary, readiness, type Sem, semaphore, stateLabel } from "../lib/api";

export function Semaphore({ sem }: { sem: Sem }) {
  return (
    <span className={`sem ${sem}`}>
      <span className="lamp" />
    </span>
  );
}

export function ReadinessBar({ value }: { value: number }) {
  return (
    <div className="bar">
      <div className="track">
        <div className="fill" style={{ width: `${Math.max(3, value)}%` }} />
      </div>
      <span className="pct">{value}%</span>
    </div>
  );
}

const STATE_CLASS: Record<string, string> = {
  READY_FOR_CUSTOMS: "ok",
  AWAITING_DOCUMENTS: "warn",
  CASE_CREATED: "accent",
};

export function StatePill({ state }: { state: string }) {
  return <span className={`pill ${STATE_CLASS[state] ?? ""}`}>{stateLabel(state)}</span>;
}

export function CaseRow({ c }: { c: CaseSummary }) {
  const r = readiness(c.customs_readiness_score);
  return (
    <tr className="row" data-href={`/cases/${c.id}`}>
      <td>
        <Semaphore sem={semaphore(c)} />
      </td>
      <td>
        <Link href={`/cases/${c.id}`} className="code">
          {c.case_number}
        </Link>
      </td>
      <td>
        <StatePill state={c.current_state} />
      </td>
      <td style={{ minWidth: 150 }}>
        <ReadinessBar value={r} />
      </td>
      <td style={{ color: "var(--muted)", fontSize: 12.5 }}>{c.blocker ?? "—"}</td>
    </tr>
  );
}
