import { Component } from "react";

/**
 * React error boundary — catches render/lifecycle errors in child tree.
 * Usage: wrap any subtree that may throw with <ErrorBoundary>.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error("[ErrorBoundary]", error, info?.componentStack);
  }

  reset() {
    this.setState({ hasError: false, error: null });
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    const fallback = this.props.fallback;
    if (fallback) return typeof fallback === "function" ? fallback(this.state.error, () => this.reset()) : fallback;

    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <div style={styles.icon}>⚠</div>
          <h3 style={styles.title}>Something went wrong</h3>
          <p style={styles.msg}>{this.state.error?.message || "An unexpected error occurred."}</p>
          <button style={styles.btn} onClick={() => this.reset()}>Try again</button>
        </div>
      </div>
    );
  }
}

const styles = {
  container: { display: "flex", alignItems: "center", justifyContent: "center", padding: "40px 20px" },
  card: { background: "#111827", border: "1px solid #1e293b", borderRadius: 12, padding: "32px 40px", textAlign: "center", maxWidth: 420 },
  icon: { fontSize: 32, marginBottom: 12 },
  title: { color: "#f1f5f9", margin: "0 0 8px", fontSize: 18 },
  msg: { color: "#94a3b8", margin: "0 0 20px", fontSize: 14, lineHeight: 1.6 },
  btn: { background: "#3b82f6", color: "#fff", border: "none", borderRadius: 6, padding: "8px 20px", cursor: "pointer", fontSize: 14 },
};
