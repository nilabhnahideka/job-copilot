/**
 * Route /applications/[id]. Reads the id from the URL and renders ApplicationView.
 * Next.js 16 requires params to be awaited inside a <Suspense> boundary.
 */
import { Suspense } from "react";
import { ApplicationView } from "@/components/ApplicationView";
import { RequireAuth } from "@/components/AuthProvider";

async function View({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <RequireAuth>
      <ApplicationView id={id} />
    </RequireAuth>
  );
}

export default function ApplicationPage({ params }: PageProps<"/applications/[id]">) {
  return (
    <Suspense fallback={<p className="text-graphite">Loading…</p>}>
      <View params={params} />
    </Suspense>
  );
}
