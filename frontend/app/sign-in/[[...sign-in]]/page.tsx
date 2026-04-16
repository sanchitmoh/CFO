import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <div
      className="flex items-center justify-center"
      style={{
        minHeight: "100vh",
        background:
          "radial-gradient(ellipse at 50% 0%, #00E5CC08 0%, var(--bg-deep) 60%)",
      }}
    >
      <SignIn
        appearance={{
          elements: {
            rootBox: "mx-auto",
            card: "bg-[#0D1321] border border-[#1E2A42] shadow-2xl",
          },
        }}
      />
    </div>
  );
}
