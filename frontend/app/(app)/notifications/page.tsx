import { apiGet, type NotificationItem, type NotificationTemplate } from "@/app/lib/api";
import { NotificationsCenter } from "@/app/components/NotificationsCenter";

export const dynamic = "force-dynamic";

export default async function NotificationsPage() {
  const notifications = (await apiGet<NotificationItem[]>("/notifications?limit=200")) ?? [];
  const templates = (await apiGet<NotificationTemplate[]>("/notifications/templates")) ?? [];

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Comunicación</div>
          <h1>Centro de notificaciones</h1>
        </div>
      </div>

      <NotificationsCenter notifications={notifications} templates={templates} />
    </>
  );
}
