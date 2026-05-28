type EmptyStateProps = {
  label: string;
};

export function EmptyState({ label }: EmptyStateProps) {
  return <div className="empty-state message">{label}</div>;
}
