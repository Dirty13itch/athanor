import { ModelObservatory } from "@/features/models/model-observatory";

export const revalidate = 15;

export default async function ModelsPage() {
  return <ModelObservatory />;
}
