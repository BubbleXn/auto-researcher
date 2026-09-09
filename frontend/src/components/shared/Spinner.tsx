import { cn } from "@/lib/cn";

export function Spinner({
  size = "md",
  className,
}: {
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const sizeClass = { sm: "w-4 h-4", md: "w-5 h-5", lg: "w-8 h-8" }[size];
  return (
    <svg
      className={cn("animate-spin text-text-secondary", sizeClass, className)}
      viewBox="0 0 24 24"
      fill="none"
    >
      <circle
        cx="12" cy="12" r="10"
        stroke="currentColor" strokeWidth="3" strokeLinecap="round"
        className="opacity-20"
      />
      <path
        d="M12 2a10 10 0 0 1 10 10"
        stroke="currentColor" strokeWidth="3" strokeLinecap="round"
      />
    </svg>
  );
}
