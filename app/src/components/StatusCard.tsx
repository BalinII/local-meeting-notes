type StatusCardProps = {
  title: string;
  description: string;
  status: string;
};

export function StatusCard({ title, description, status }: StatusCardProps) {
  return (
    <article className="status-card">
      <div className="status-pill">{status}</div>
      <h2>{title}</h2>
      <p>{description}</p>
    </article>
  );
}
