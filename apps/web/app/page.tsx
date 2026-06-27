import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-6 p-8 text-center">
      <h1 className="text-4xl font-bold tracking-tight">SarkariJobAI</h1>
      <p className="text-muted-foreground max-w-md text-lg">
        Stop scrolling through thousands of govt job notifications. See only the
        ones <strong>you are actually eligible for</strong>.
      </p>
      <div className="flex gap-4">
        <Link href="/register" className={buttonVariants()}>Get Started</Link>
        <Link href="/login" className={buttonVariants({ variant: "outline" })}>Sign In</Link>
      </div>
    </main>
  );
}
