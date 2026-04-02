import { TodosConsole } from "@/features/operator/todos-console";

export const revalidate = 15;

export default async function TodosPage() {
  return <TodosConsole />;
}
