import { BootstrapConsole } from "@/features/operator/bootstrap-console";

export const revalidate = 15;

export default async function BootstrapPage() {
  return <BootstrapConsole />;
}
