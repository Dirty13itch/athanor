import { redirect } from "next/navigation";

export const revalidate = 15;

export default async function TasksPage() {
  redirect("/runs");
}
