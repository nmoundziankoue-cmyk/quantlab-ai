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
          <div style={styles.icon}>ERROR</div>
          <h3 style={styles.title}>Something went wrong</h3>
          <p style={styles.msg}>{this.state.error?.message || "An unexpected error occurred."}</p>
          <button style={styles.btn} onClick={() => this.reset()}>Try again</button>
        </div>
      </div>
    );
  }
}

const styles = {
  container: { display: "flex", alignItems: "center", justifyContent: "center", padding: "60px 20px", minHeight: 300 },
  card: { background: "var(--panel, #131720)", border: "1px solid var(--border, #232A3D)", borderRadius: 8, padding: "32px 40px", textAlign: "center", maxWidth: 440 },
  icon: { fontFamily: "var(--font-mono, monospace)", fontSize: 11, color: "var(--negative, #E5473E)", letterSpacing: "0.1em", marginBottom: 14 },
  title: { fontFamily: "var(--font-display, sans-serif)", color: "var(--text-1, #DDE2EE)", margin: "0 0 8px", fontSize: 17, fontWeight: 700 },
  msg: { fontFamily: "var(--font-body, sans-serif)", color: "var(--text-3, #454D66)", margin: "0 0 24px", fontSize: 13, lineHeight: 1.6 },
  btn: { fontFamily: "var(--font-mono, monospace)", background: "var(--accent, #567EFF)22", color: "var(--accent, #567EFF)", border: "1px solid var(--accent, #567EFF)55", borderRadius: 6, padding: "8px 20px", cursor: "pointer", fontSize: 12 },
};
