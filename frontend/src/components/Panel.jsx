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
    accent: "bg-surface border border-border border-l-2 border-l-accent shadow-accent",
    glass: "bg-surface/80 border border-border/70 backdrop-blur-sm",
  };

  return (
    <section
      className={clsx(
        "min-w-0 overflow-hidden rounded-xl transition-colors duration-200 hover:border-border/90",
        variantStyles[variant] || variantStyles.default,
        className
      )}
    >
      {(title || action) && (
        <div className="flex items-center justify-between gap-4 border-b border-border px-5 py-4">
          <div className="min-w-0">
            {title && <h3 className="font-display text-sm font-semibold tracking-wide text-text">{title}</h3>}
            {subtitle && <p className="mt-1 text-xs text-textMuted">{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      <div className="p-5">
        {loading ? <PanelSkeleton /> : children}
      </div>
    </section>
  );
}

function PanelSkeleton() {
  return (
    <div className="animate-pulse space-y-3" aria-label="Loading">
      <div className="skeleton h-4 w-3/4" />
      <div className="skeleton h-4 w-1/2" />
      <div className="skeleton h-4 w-5/6" />
    </div>
  );
}
