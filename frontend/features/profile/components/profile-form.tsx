"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { RequestFailedError, type TeacherProfile } from "@/lib/api";
import { useSaveTeacherProfile } from "../hooks/use-teacher-profile";

export function ProfileForm({ initial }: { initial: TeacherProfile | null }) {
  const save = useSaveTeacherProfile();
  const [subject, setSubject] = useState(initial?.subject ?? "");
  const [className, setClassName] = useState(initial?.class_name ?? "");
  const [studentsNote, setStudentsNote] = useState(initial?.students_note ?? "");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await save.mutateAsync({
        subject: subject.trim(),
        class_name: className.trim(),
        students_note: studentsNote.trim(),
      });
      toast.success("حُفظ بروفايل المعلم.");
    } catch (error) {
      toast.error(
        error instanceof RequestFailedError
          ? error.message
          : "تعذر حفظ بروفايل المعلم.",
      );
    }
  }

  const disabled = save.isPending || !subject.trim() || !className.trim();

  return (
    <form className="mt-6 space-y-5" onSubmit={handleSubmit}>
      <div className="space-y-2">
        <Label htmlFor="profile-subject">المادة</Label>
        <Input
          id="profile-subject"
          value={subject}
          maxLength={100}
          placeholder="اللغة العربية - النحو"
          onChange={(event) => setSubject(event.target.value)}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="profile-class">الصف</Label>
        <Input
          id="profile-class"
          value={className}
          maxLength={100}
          placeholder="الثاني المتوسط"
          onChange={(event) => setClassName(event.target.value)}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="profile-note">ملاحظة عن الطلاب</Label>
        <Textarea
          id="profile-note"
          value={studentsNote}
          maxLength={1000}
          rows={3}
          placeholder="عدد الطلاب، مستوياتهم، نقاط ضعفهم"
          onChange={(event) => setStudentsNote(event.target.value)}
        />
      </div>
      <Button type="submit" disabled={disabled}>
        {save.isPending ? "جارٍ الحفظ..." : "حفظ البروفايل"}
      </Button>
    </form>
  );
}
