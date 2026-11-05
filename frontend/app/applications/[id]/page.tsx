import { Suspense } from "react";
import { ApplicationView } from "@/components/ApplicationView";

async function View({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ApplicationView id={id} />;
}

export default function ApplicationPage({ params }: PageProps<"/applications/[id]">) {
  return (
    <Suspense fallback={<p className="text-graphite">Loading…</p>}>
      <View params={params} />
    </Suspense>
  );
}
