import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { apiGet, type KcUser, type RolePrivilege } from "@/app/lib/api";
import { capsFromRoles, parseRolesCookie } from "@/app/lib/rbac";
import { RolePrivilegeMatrix } from "@/app/components/RolePrivilegeMatrix";
import { UsersManager } from "@/app/components/UsersManager";

export const dynamic = "force-dynamic";

export default async function AdminPage() {
  // Solo el super administrador. El backend también lo exige (defensa en profundidad).
  const caps = capsFromRoles(parseRolesCookie(cookies().get("caop_roles")?.value));
  if (!caps.isSuperAdmin) redirect("/");

  const [roles, users, realmRoles] = await Promise.all([
    apiGet<RolePrivilege[]>("/admin/roles"),
    apiGet<KcUser[]>("/admin/users"),
    apiGet<string[]>("/admin/realm-roles"),
  ]);

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Configuración · Seguridad</div>
          <h1>Usuarios y privilegios</h1>
        </div>
      </div>

      <div
        className="blocker-banner section-gap"
        style={{
          background: "rgba(45,212,191,0.08)",
          borderColor: "rgba(45,212,191,0.3)",
          color: "var(--muted)",
        }}
      >
        Panel exclusivo del <b>super administrador</b>. <b>admin-caop</b> (rol
        SUPER_ADMIN) mantiene poder total y no es editable. Aquí se gestionan las cuentas
        del personal, sus roles y las capacidades de cada rol.
      </div>

      <UsersManager users={users ?? []} realmRoles={realmRoles ?? []} />

      <div className="section-gap" />

      <RolePrivilegeMatrix roles={roles ?? []} />
    </>
  );
}
