export default function Panel({ title, subtitle, action, children, className = "" }) {
  return (
    <div className={`bg-surface border border-border rounded-lg ${className}`}>
      {(title || action) && (
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <div>
            {title && (
              <h3 className="font-display font-semibold text-sm text-text tracking-wide">
                {title}
              </h3>
            )}
            {subtitle && <p className="text-xs text-textMuted mt-0.5">{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}
