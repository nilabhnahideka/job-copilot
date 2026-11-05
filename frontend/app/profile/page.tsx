/** Route /profile. Your profile, filled in once and used for every application. */
import { RequireAuth } from "@/components/AuthProvider";
import { ProfileView } from "@/components/ProfileView";

export default function ProfilePage() {
  return (
    <RequireAuth>
      <ProfileView />
    </RequireAuth>
  );
}
