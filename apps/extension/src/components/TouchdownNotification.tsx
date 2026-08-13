type Props = { message: string | null };

export function TouchdownNotification({ message }: Props) {
  if (!message) return null;

  return (
    <div className="touchdown-notification" role="status" aria-live="polite">
      <span className="touchdown-icon" aria-hidden="true">🏈</span>
      <div>
        <strong>TOUCHDOWN</strong>
        <p>{message}</p>
      </div>
    </div>
  );
}
