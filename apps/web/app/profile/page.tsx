"use client";
import { useEffect } from "react";
import { useForm, type Resolver } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";

const schema = z.object({
  dob: z.string().min(1, "Date of birth is required"),
  category: z.enum(["Gen", "OBC", "SC", "ST", "EWS"]),
  gender: z.enum(["male", "female", "other"]),
  state: z.string().min(1, "State is required"),
  qualification_level: z.enum(["10th", "12th", "diploma", "graduate", "postgraduate", "phd"]),
  qualification_percentage: z.number().min(0).max(100).optional(),
  experience_years: z.number().min(0).default(0),
  is_pwd: z.boolean().default(false),
  is_ex_serviceman: z.boolean().default(false),
});

type Form = z.infer<typeof schema>;

const STATES = [
  "Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh","Goa","Gujarat",
  "Haryana","Himachal Pradesh","Jharkhand","Karnataka","Kerala","Madhya Pradesh",
  "Maharashtra","Manipur","Meghalaya","Mizoram","Nagaland","Odisha","Punjab",
  "Rajasthan","Sikkim","Tamil Nadu","Telangana","Tripura","Uttar Pradesh",
  "Uttarakhand","West Bengal","Delhi","Jammu & Kashmir","Ladakh",
];

export default function ProfilePage() {
  const router = useRouter();
  const qc = useQueryClient();

  const { data: profile, isLoading } = useQuery({
    queryKey: ["profile"],
    queryFn: api.getProfile,
  });

  const { register, handleSubmit, setValue, watch, reset, formState: { errors, isSubmitting } } = useForm<Form>({
    resolver: zodResolver(schema) as Resolver<Form>,
    defaultValues: { experience_years: 0, is_pwd: false, is_ex_serviceman: false },
  });

  useEffect(() => {
    if (profile) {
      reset({
        dob: profile.dob ? String(profile.dob).slice(0, 10) : "",
        category: profile.category as Form["category"] || "Gen",
        gender: profile.gender as Form["gender"] || "male",
        state: profile.state as string || "",
        qualification_level: profile.qualification_level as Form["qualification_level"] || "graduate",
        qualification_percentage: profile.qualification_percentage as number || undefined,
        experience_years: profile.experience_years as number || 0,
        is_pwd: profile.is_pwd as boolean || false,
        is_ex_serviceman: profile.is_ex_serviceman as boolean || false,
      });
    }
  }, [profile, reset]);

  const mutation = useMutation({
    mutationFn: (data: Form) => api.updateProfile(data),
    onSuccess: () => {
      toast.success("Profile updated!");
      qc.invalidateQueries({ queryKey: ["jobs"] });
      router.push("/jobs");
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Update failed"),
  });

  if (isLoading) return <div className="p-6 text-center">Loading profile…</div>;

  return (
    <main className="max-w-lg mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Your Profile</h1>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Eligibility Details</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <Label>Date of Birth</Label>
                <Input type="date" {...register("dob")} />
                {errors.dob && <p className="text-xs text-destructive">{errors.dob.message}</p>}
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Gender</Label>
                <Select value={watch("gender")} onValueChange={(v) => v && setValue("gender", v as Form["gender"])}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="male">Male</SelectItem>
                    <SelectItem value="female">Female</SelectItem>
                    <SelectItem value="other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <Label>Category</Label>
                <Select value={watch("category")} onValueChange={(v) => setValue("category", v as Form["category"])}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {["Gen","OBC","SC","ST","EWS"].map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Home State</Label>
                <Select value={watch("state") ?? ""} onValueChange={(v) => v && setValue("state", v)}>
                  <SelectTrigger><SelectValue placeholder="Select state" /></SelectTrigger>
                  <SelectContent>
                    {STATES.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                  </SelectContent>
                </Select>
                {errors.state && <p className="text-xs text-destructive">{errors.state.message}</p>}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <Label>Highest Qualification</Label>
                <Select value={watch("qualification_level")} onValueChange={(v) => v && setValue("qualification_level", v as Form["qualification_level"])}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {["10th","12th","diploma","graduate","postgraduate","phd"].map(q => (
                      <SelectItem key={q} value={q}>{q}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Percentage / CGPA</Label>
                <Input type="number" step="0.1" placeholder="e.g. 75" {...register("qualification_percentage", { valueAsNumber: true })} />
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label>Years of Experience</Label>
              <Input type="number" min="0" {...register("experience_years", { valueAsNumber: true })} />
            </div>

            <div className="flex gap-6">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" {...register("is_pwd")} className="w-4 h-4" />
                Person with Disability (PwD)
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" {...register("is_ex_serviceman")} className="w-4 h-4" />
                Ex-Serviceman
              </label>
            </div>

            <Button type="submit" disabled={isSubmitting || mutation.isPending}>
              {mutation.isPending ? "Saving…" : "Save & View Jobs"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
