// Capacidades por rol (espejo del RBAC del backend). Seguro en server y client.

export const WRITER_ROLES = [
  "SUPER_ADMIN", "OPERATIONS_MANAGER", "CUSTOMS_AGENT", "CUSTOMS_ASSISTANT",
  "OCEAN_OPERATOR", "AIR_OPERATOR", "DOCUMENT_SPECIALIST", "SALES", "FINANCE", "API_SERVICE",
];
export const ADMIN_ROLES = ["SUPER_ADMIN", "OPERATIONS_MANAGER"];
export const SIGN_ROLES = ["CUSTOMS_AGENT", "SUPER_ADMIN"];
export const STAFF_ROLES = [...WRITER_ROLES, "AUDITOR"];

export interface Caps {
  roles: string[];
  canWrite: boolean;
  canSign: boolean;
  canAdmin: boolean;
  isViewer: boolean;
  isStaff: boolean;
  isCustomer: boolean;
  isCustomerOnly: boolean;
}

export function capsFromRoles(roles: string[]): Caps {
  const has = (set: string[]) => roles.some((r) => set.includes(r));
  const canWrite = has(WRITER_ROLES);
  const isStaff = has(STAFF_ROLES);
  const isCustomer = roles.includes("CUSTOMER");
  return {
    roles,
    canWrite,
    canSign: has(SIGN_ROLES),
    canAdmin: has(ADMIN_ROLES),
    isViewer: !canWrite,
    isStaff,
    isCustomer,
    isCustomerOnly: isCustomer && !isStaff,
  };
}

export function parseRolesCookie(raw: string | undefined | null): string[] {
  return raw ? raw.split(",").map((s) => s.trim()).filter(Boolean) : [];
}
