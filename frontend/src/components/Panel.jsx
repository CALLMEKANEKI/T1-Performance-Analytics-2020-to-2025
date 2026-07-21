import clsx from "clsx";

export default function Panel({
  title,
  subtitle,
  action,
  children,
  className = "",
  variant = "default",
  loading = false,
}) {
  const variantStyles = {
    default: "bg-surface border border-border",
    accent: "bg-surface border border-border border-l-2 border-l-accent shadow-[0_0_12px_rgba(224,20,76,0.08)]",
    glass: "backdrop-blur-sm bg-surface/80 border border-border/50",
  };

  return (
    <div
      className={clsx(
        "rounded-xl transition-colors duration-200 hover:border-border/80",
        variantStyles[variant],
        className
      )}
    >
      {(title || action) && (
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <div>
            {title && (
              <h3 className="font-display font-semibold text-sm tracking-wide text-text">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-xs uppercase tracking-widest text-textMuted mt-0.5">
                {subtitle}
              </p>
            )}
          </div>
          {action}
        </div>
      )}
      <div className="p-5">
        {loading ? <PanelSkeleton /> : children}
      </div>
    </div>
  );
}

function PanelSkeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      <div className="skeleton h-4 w-3/4" />
      <div className="skeleton h-4 w-1/2" />
      <div className="skeleton h-4 w-5/6" />
    </div>
  );
}