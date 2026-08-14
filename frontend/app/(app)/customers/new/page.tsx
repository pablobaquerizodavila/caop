import Link from "next/link";

import { NewCustomerForm } from "@/app/components/NewCustomerForm";

export const dynamic = "force-dynamic";

export default function NewCustomerPage() {
  return (
    <>
      <div className="eyebrow" style={{ marginBottom: 10 }}>
        <Link href="/customers" style={{ color: "var(--accent)" }}>
          ← Clientes
        </Link>
      </div>
      <div className="topbar">
        <div>
          <div className="eyebrow">CRM</div>
          <h1>Nuevo cliente</h1>
        </div>
      </div>
      <div className="card card-pad rise">
        <NewCustomerForm />
      </div>
    </>
  );
}
