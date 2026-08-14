"use client";

import { useEffect, useState } from "react";

import { type Caps, capsFromRoles, parseRolesCookie } from "@/app/lib/rbac";

function readRolesCookie(): string[] {
  if (typeof document === "undefined") return [];
  const m = document.cookie.match(/(?:^|;\s*)caop_roles=([^;]*)/);
  return parseRolesCookie(m ? decodeURIComponent(m[1]) : "");
}

/** Capacidades del usuario según la cookie caop_roles (no httpOnly).
 *  La aplicación real del RBAC está en el backend; esto solo oculta acciones. */
export function useCaps(): Caps {
  const [roles, setRoles] = useState<string[]>([]);
  useEffect(() => {
    setRoles(readRolesCookie());
  }, []);
  return capsFromRoles(roles);
}
