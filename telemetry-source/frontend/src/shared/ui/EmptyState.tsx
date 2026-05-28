type EmptyStateProps = {
  label: string;
};

export function EmptyState({ label }: EmptyStateProps) {
  return <div className="message">{label}</div>;
}
