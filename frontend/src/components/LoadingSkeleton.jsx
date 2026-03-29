export default function LoadingSkeleton({ rows = 5, cols = 6 }) {
  return (
    <div className="animate-pulse space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4">
          {Array.from({ length: cols }).map((_, j) => (
            <div key={j} className="h-4 bg-[#A9B8E2]/30 rounded flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}
