"use client";

import { useEffect, useRef, useState } from "react";

import { searchTariffCodes, type TariffSuggestion } from "@/app/lib/actions";

/** Autocompletar de subpartida contra el maestro arancelario. Busca por texto o por
 *  prefijo de código. Al elegir, fija el código (y opcionalmente descripción/unidad). */
export function SubpartidaInput({
  value,
  onChange,
  onPick,
  placeholder = "Subpartida (HS)",
}: {
  value: string;
  onChange: (v: string) => void;
  onPick?: (s: TariffSuggestion) => void;
  placeholder?: string;
}) {
  const [suggestions, setSuggestions] = useState<TariffSuggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!value || value.trim().length < 2) {
      setSuggestions([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    const t = setTimeout(async () => {
      const res = await searchTariffCodes(value);
      if (!cancelled) {
        setSuggestions(res);
        setLoading(false);
      }
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [value]);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  return (
    <div ref={boxRef} style={{ position: "relative", width: "100%" }}>
      <input
        type="text"
        placeholder={placeholder}
        value={value}
        autoComplete="off"
        style={{ width: "100%", boxSizing: "border-box" }}
        onChange={(e) => {
          onChange(e.target.value);
          setOpen(true);
        }}
        onFocus={() => value.trim().length >= 2 && setOpen(true)}
      />
      {open && (suggestions.length > 0 || loading) ? (
        <div
          style={{
            position: "absolute", zIndex: 30, top: "calc(100% + 2px)", left: 0,
            minWidth: 320, maxWidth: 460, maxHeight: 260, overflowY: "auto",
            background: "var(--surface, #fff)", border: "1px solid var(--border, #ccc)",
            borderRadius: 8, boxShadow: "0 8px 24px rgba(0,0,0,0.18)",
          }}
        >
          {loading && suggestions.length === 0 ? (
            <div style={{ padding: "8px 12px", color: "var(--muted)", fontSize: 12.5 }}>
              Buscando…
            </div>
          ) : null}
          {suggestions.map((s) => (
            <button
              type="button"
              key={s.code}
              onClick={() => {
                onChange(s.code);
                onPick?.(s);
                setOpen(false);
              }}
              style={{
                display: "block", width: "100%", textAlign: "left", padding: "7px 12px",
                background: "transparent", border: "none", borderBottom: "1px solid var(--border)",
                cursor: "pointer", fontSize: 12.5, color: "var(--text)",
              }}
            >
              <span className="mono" style={{ color: "var(--accent)" }}>{s.code}</span>
              {s.ad_valorem != null ? (
                <span style={{ color: "var(--muted-2)", marginLeft: 8 }}>
                  Ad-Val {String(s.ad_valorem)}%
                </span>
              ) : null}
              <div style={{ color: "var(--muted)", marginTop: 2 }}>
                {(s.full_description || s.description || "").slice(0, 90)}
              </div>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
