import { cn } from "@/lib/utils";

interface LoadingProps {
  message?: string;
  className?: string;
}

export function Loading({ message, className }: LoadingProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 py-12",
        className
      )}
    >
      <div className="w-5 h-5 rounded-full border-2 border-[#3a3a3c] border-t-[#0a84ff] animate-spin" />
      <p className="text-[13px] text-[#98989d]">{message ?? "Loading..."}</p>
    </div>
  );
}
