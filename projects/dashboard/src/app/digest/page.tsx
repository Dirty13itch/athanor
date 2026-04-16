import { DigestConsole } from "@/features/digest/digest-console";

export const revalidate = 15;

export default async function DigestPage() {
  return <DigestConsole />;
}
