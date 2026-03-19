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

export function Skeleton({ className }: { className?: string }) {
  return (
    <div className={`animate-pulse bg-[#3a3a3c] rounded-lg ${className ?? ""}`} />
  );
}

export function CardSkeleton() {
  return (
    <div className="bg-[#2c2c2e] border border-[#3a3a3c] rounded-[10px] p-4 space-y-3">
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-3 w-1/2" />
      <Skeleton className="h-3 w-1/4" />
    </div>
  );
}

export function FeedSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  );
}

export function ChartSkeleton() {
  return (
    <div className="border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] p-5 space-y-4">
      <Skeleton className="h-3 w-1/3" />
      <Skeleton className="h-[200px] w-full" />
    </div>
  );
}

export function AnalyticsSkeleton() {
  return (
    <div className="space-y-6">
      {Array.from({ length: 4 }).map((_, i) => (
        <ChartSkeleton key={i} />
      ))}
    </div>
  );
}
