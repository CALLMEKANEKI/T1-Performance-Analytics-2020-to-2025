export const TOOLTIP_STYLE = {
  contentStyle: {
    backgroundColor: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: 8,
    fontSize: 12,
    color: "var(--color-text)",
  },
  labelStyle: { color: "var(--color-text)" },
  itemStyle: { color: "var(--color-text)" },
  cursor: { fill: "var(--shimmer-high)" },
};

export const CHART_COLORS = {
  accent: "var(--color-accent)",
  border: "var(--color-border)",
  text: "var(--color-text)",
  textMuted: "var(--color-text-muted)",
  win: "var(--color-win)",
  blue: "var(--color-blue)",
  amber: "var(--color-amber)",
  purple: "var(--color-purple)",
};

export const LEGEND_PROPS = {
  iconType: "circle",
  iconSize: 8,
  wrapperStyle: { fontSize: 12, color: CHART_COLORS.textMuted },
};

export function legendFormatter(labels = {}) {
  return (value) => labels[value] ?? value;
}

export function axisProps(fontSize = 10) {
  return {
    tick: { fontSize, fill: CHART_COLORS.textMuted },
    tickLine: false,
    axisLine: { stroke: CHART_COLORS.border },
  };
}

export default {
  TOOLTIP_STYLE,
};
