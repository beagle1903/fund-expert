export default function ErrorPanel({ message }) {
  return (
    <div className="glass-panel error-panel" role="alert">
      <h3>Error</h3>
      <p>{message}</p>
    </div>
  );
}
