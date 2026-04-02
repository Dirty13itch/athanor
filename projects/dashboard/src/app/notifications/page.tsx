import { redirect } from "next/navigation";

export const revalidate = 15;

export default async function NotificationsPage() {
  redirect("/inbox");
}
