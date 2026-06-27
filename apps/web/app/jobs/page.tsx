"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api, Job } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";

function JobCard({ job }: { job: Job }) {
  const deadline = job.deadline ? new Date(job.deadline) : null;
  const isExpiringSoon = deadline && (deadline.getTime() - Date.now()) < 7 * 24 * 60 * 60 * 1000;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base leading-snug">{job.title}</CardTitle>
          {isExpiringSoon && <Badge variant="destructive" className="shrink-0">Closing Soon</Badge>}
        </div>
        <p className="text-sm text-muted-foreground">{job.organization}</p>
      </CardHeader>
      <CardContent className="flex items-center justify-between gap-4">
        <div className="text-sm text-muted-foreground">
          {deadline ? (
            <span>Deadline: {deadline.toLocaleDateString("en-IN")}</span>
          ) : (
            <span>No deadline listed</span>
          )}
        </div>
        {job.apply_url && (
          <a
            href={job.apply_url}
            target="_blank"
            rel="noopener noreferrer"
            className={buttonVariants({ size: "sm" })}
          >
            Apply
          </a>
        )}
      </CardContent>
    </Card>
  );
}

export default function JobsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => api.getJobs(),
  });

  return (
    <main className="max-w-2xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Your Eligible Jobs</h1>
          {data && <p className="text-muted-foreground text-sm">{data.total} jobs match your profile</p>}
        </div>
        <div className="flex gap-2">
          <Link href="/profile" className={buttonVariants({ variant: "outline", size: "sm" })}>
            Edit Profile
          </Link>
        </div>
      </div>

      {isLoading && (
        <div className="flex flex-col gap-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-28 rounded-lg bg-muted animate-pulse" />
          ))}
        </div>
      )}

      {error && (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            <p>Could not load jobs. <Link href="/login" className="underline">Sign in again</Link></p>
          </CardContent>
        </Card>
      )}

      {data?.message && (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-muted-foreground mb-4">{data.message}</p>
            <Link href="/profile" className={buttonVariants()}>Complete Profile</Link>
          </CardContent>
        </Card>
      )}

      {data?.jobs && data.jobs.length === 0 && !data.message && (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            No eligible jobs found right now. Check back after the next scrape (every 6 hours).
          </CardContent>
        </Card>
      )}

      <div className="flex flex-col gap-3">
        {data?.jobs?.map((job) => <JobCard key={job.id} job={job} />)}
      </div>
    </main>
  );
}
