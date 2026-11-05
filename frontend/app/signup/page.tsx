/** Route /signup. New accounts go to the profile page next. */
import { AuthForm } from "@/components/AuthForm";

export default function SignupPage() {
  return <AuthForm mode="signup" />;
}
