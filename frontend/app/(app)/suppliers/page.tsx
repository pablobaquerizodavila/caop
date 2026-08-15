import { apiGet, type Supplier } from "@/app/lib/api";
import { SuppliersManager } from "@/app/components/SuppliersManager";

export const dynamic = "force-dynamic";

export default async function SuppliersPage() {
  const suppliers = (await apiGet<Supplier[]>("/suppliers?limit=200")) ?? [];

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">CRM · Comercio exterior</div>
          <h1>Proveedores</h1>
        </div>
      </div>

      <SuppliersManager suppliers={suppliers} />
    </>
  );
}
