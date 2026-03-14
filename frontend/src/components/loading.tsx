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
      <div className="w-6 h-6 rounded-full border-2 border-zinc-700 border-t-zinc-300 animate-spin" />
      {message && <p className="text-zinc-500 text-sm">{message}</p>}
    </div>
  );
}
