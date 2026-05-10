import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <div
      className="flex items-center justify-center"
      style={{
        minHeight: "100vh",
        background:
          "radial-gradient(ellipse at 50% 0%, #C9A96208 0%, var(--bg-deep) 60%)",
      }}
    >
      <SignIn
        appearance={{
          elements: {
            rootBox: "mx-auto",
            card: "bg-[#111111] border border-[#232323] shadow-2xl",
          },
        }}
      />
    </div>
  );
}
