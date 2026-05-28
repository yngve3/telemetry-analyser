type StatusPillProps = {
  label: string;
  tone?: "success" | "warning" | "danger" | "neutral";
};

export function StatusPill({ label, tone = "neutral" }: StatusPillProps) {
  return <span className={`status-pill ${tone}`}>{label}</span>;
}
