import { SignIn } from "@clerk/nextjs";
import { AuthShell } from "@/components/auth/AuthShell";

export default function SignInPage() {
  return (
    <AuthShell
      mode="sign-in"
      eyebrow="Welcome back"
      title="Return to your financial command center."
      description="Sign in to continue monitoring runway, spend patterns, and the decisions waiting on your next move."
    >
      <SignIn
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
