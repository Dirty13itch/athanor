import { DirectChatConsole } from "@/features/chat/direct-chat-console";
import { getModelsSnapshot } from "@/lib/dashboard-data";

export const revalidate = 30;

export default async function ChatPage() {
  const models = await getModelsSnapshot();
  return <DirectChatConsole initialModels={models} />;
}
