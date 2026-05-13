import { SignUp } from "@clerk/nextjs";
import { AuthShell } from "@/components/auth/AuthShell";

export default function SignUpPage() {
  return (
    <AuthShell
      mode="sign-up"
      eyebrow="Create workspace"
      title="Set up the room where finance gets clearer."
      description="Start your workspace without changing the familiar Clerk flow, then bring your team into a calmer operating rhythm."
    >
      <SignUp
        appearance={{
          elements: {
            rootBox: "auth-clerk-root",
            card: "auth-clerk-card",
          },
        }}
      />
    </AuthShell>
  );
}
