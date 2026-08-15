// Gráficos SVG puros (sin dependencias externas). Componentes de servidor.

const PALETTE = [
  "var(--accent)", "var(--ok)", "var(--warn)", "var(--risk)",
  "var(--crit)", "var(--accent-dim)", "#8b5cf6", "#38bdf8", "#f472b6", "#a3e635",
];

export interface Slice {
  label: string;
  value: number;
}

export function Donut({ data, size = 168 }: { data: Slice[]; size?: number }) {
  const entries = data.filter((d) => d.value > 0);
  const total = entries.reduce((s, d) => s + d.value, 0);
  const r = size / 2 - 16;
  const cx = size / 2;
  const c = 2 * Math.PI * r;

  if (total === 0) {
    return <div className="empty" style={{ padding: 24 }}>Sin datos.</div>;
  }

  let acc = 0;
  return (
    <div style={{ display: "flex", gap: 18, alignItems: "center", flexWrap: "wrap", padding: "6px 18px 16px" }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img">
        <circle cx={cx} cy={cx} r={r} fill="none" stroke="var(--surface-3)" strokeWidth={16} />
        {entries.map((d, i) => {
          const frac = d.value / total;
          const dash = frac * c;
          const el = (
            <circle
              key={d.label}
              cx={cx}
              cy={cx}
              r={r}
              fill="none"
              stroke={PALETTE[i % PALETTE.length]}
              strokeWidth={16}
              strokeDasharray={`${dash} ${c - dash}`}
              strokeDashoffset={-acc}
              transform={`rotate(-90 ${cx} ${cx})`}
              strokeLinecap="butt"
            />
          );
          acc += dash;
          return el;
        })}
        <text x={cx} y={cx - 2} textAnchor="middle" fontSize="26" fontWeight="600" fill="var(--text)" fontFamily="var(--mono)">
          {total}
        </text>
        <text x={cx} y={cx + 16} textAnchor="middle" fontSize="10" fill="var(--muted-2)">total</text>
      </svg>
      <div style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 150 }}>
        {entries.map((d, i) => (
          <div key={d.label} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12.5 }}>
            <span style={{ width: 10, height: 10, borderRadius: 3, background: PALETTE[i % PALETTE.length], flex: "none" }} />
            <span style={{ color: "var(--muted)", flex: 1 }}>{d.label}</span>
            <span className="mono" style={{ color: "var(--text)" }}>{d.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export interface LineSeries {
  label: string;
  color: string;
  points: number[];
}

export function LineChart({
  labels,
  series,
  height = 200,
}: {
  labels: string[];
  series: LineSeries[];
  height?: number;
}) {
  const w = 640;
  const pad = { l: 34, r: 12, t: 14, b: 26 };
  const n = labels.length;
  if (n === 0) return <div className="empty" style={{ padding: 24 }}>Sin datos.</div>;

  const max = Math.max(1, ...series.flatMap((s) => s.points));
  const innerW = w - pad.l - pad.r;
  const innerH = height - pad.t - pad.b;
  const x = (i: number) => pad.l + (n === 1 ? innerW / 2 : (i / (n - 1)) * innerW);
  const y = (v: number) => pad.t + innerH - (v / max) * innerH;

  return (
    <div style={{ overflowX: "auto", padding: "8px 18px 12px" }}>
      <svg width={w} height={height} viewBox={`0 0 ${w} ${height}`} role="img" style={{ maxWidth: "100%" }}>
        {[0, 0.5, 1].map((f) => (
          <line key={f} x1={pad.l} x2={w - pad.r} y1={pad.t + innerH * (1 - f)} y2={pad.t + innerH * (1 - f)}
            stroke="var(--border-soft)" strokeWidth={1} />
        ))}
        {[0, 0.5, 1].map((f) => (
          <text key={f} x={pad.l - 6} y={pad.t + innerH * (1 - f) + 3} textAnchor="end" fontSize="9" fill="var(--muted-2)" fontFamily="var(--mono)">
            {Math.round(max * f)}
          </text>
        ))}
        {series.map((s) => (
          <polyline key={s.label} fill="none" stroke={s.color} strokeWidth={2}
            points={s.points.map((v, i) => `${x(i)},${y(v)}`).join(" ")} />
        ))}
        {series.map((s) =>
          s.points.map((v, i) => (
            <circle key={`${s.label}-${i}`} cx={x(i)} cy={y(v)} r={2.5} fill={s.color} />
          )),
        )}
        {labels.map((l, i) => (
          <text key={l} x={x(i)} y={height - 8} textAnchor="middle" fontSize="9" fill="var(--muted-2)" fontFamily="var(--mono)">
            {l.slice(2)}
          </text>
        ))}
      </svg>
      <div style={{ display: "flex", gap: 16, paddingLeft: pad.l }}>
        {series.map((s) => (
          <span key={s.label} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
            <span style={{ width: 10, height: 3, background: s.color, display: "inline-block" }} />
            <span style={{ color: "var(--muted)" }}>{s.label}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
