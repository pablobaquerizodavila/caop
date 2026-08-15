"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function GlobalSearch() {
  const router = useRouter();
  const [q, setQ] = useState("");

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const term = q.trim();
    if (term.length >= 2) router.push(`/search?q=${encodeURIComponent(term)}`);
  }

  return (
    <form onSubmit={submit}>
      <input
        type="search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Buscar…"
        aria-label="Búsqueda global"
        style={{ width: "100%", fontSize: 13 }}
      />
    </form>
  );
}
