import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import useAuthStore from "../store/useAuthStore";

const s = {
  page: {
    minHeight: "100vh",
    background: "#0d1117",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontFamily: "'Inter', system-ui, sans-serif",
    color: "#e6edf3",
  },
  card: {
    background: "#161b22",
    border: "1px solid #30363d",
    borderRadius: 12,
    padding: "40px 36px",
    width: "100%",
    maxWidth: 400,
  },
  logo: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    marginBottom: 28,
  },
  logoQ: {
    width: 32,
    height: 32,
    borderRadius: 8,
    background: "#2563eb",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 700,
    fontSize: 16,
    color: "#fff",
  },
  logoName: { fontWeight: 700, fontSize: 18, color: "#e6edf3" },
  title: { fontSize: 20, fontWeight: 700, margin: "0 0 6px" },
  subtitle: { fontSize: 13, color: "#8b949e", margin: "0 0 28px" },
  label: { display: "block", fontSize: 13, color: "#8b949e", marginBottom: 6 },
  input: {
    width: "100%",
    background: "#0d1117",
    border: "1px solid #30363d",
    borderRadius: 8,
    color: "#e6edf3",
    fontSize: 14,
    padding: "10px 14px",
    marginBottom: 18,
    outline: "none",
    boxSizing: "border-box",
    transition: "border-color 0.15s",
  },
  btn: {
    width: "100%",
    background: "#238636",
    border: "none",
    borderRadius: 8,
    color: "#fff",
    fontWeight: 600,
    fontSize: 14,
    padding: "12px 0",
    cursor: "pointer",
    marginTop: 4,
  },
  btnDisabled: { opacity: 0.6, cursor: "not-allowed" },
  error: {
    background: "#2d1b1b",
    border: "1px solid #f85149",
    borderRadius: 6,
    color: "#f85149",
    fontSize: 13,
    padding: "10px 14px",
    marginBottom: 16,
  },
  footer: { marginTop: 20, fontSize: 13, color: "#8b949e", textAlign: "center" },
  link: { color: "#58a6ff", textDecoration: "none" },
};

export default function Login() {
  const navigate = useNavigate();
  const { login, isLoading, error, clearError } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    clearError();
    try {
      await login(email.trim().toLowerCase(), password);
      navigate("/", { replace: true });
    } catch {
      // error is already set in the store
    }
  };

  return (
    <div style={s.page}>
      <div style={s.card}>
        <div style={s.logo}>
          <div style={s.logoQ}>Q</div>
          <span style={s.logoName}>QuantLab AI</span>
        </div>

        <h1 style={s.title}>Sign in</h1>
        <p style={s.subtitle}>Welcome back to your institutional trading platform</p>

        {error && <div style={s.error}>{error}</div>}

        <form onSubmit={handleSubmit}>
          <label style={s.label}>Email address</label>
          <input
            type="email"
            style={s.input}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="analyst@example.com"
            required
            autoComplete="email"
            autoFocus
          />

          <label style={s.label}>Password</label>
          <input
            type="password"
            style={s.input}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            required
            autoComplete="current-password"
          />

          <button
            type="submit"
            style={{ ...s.btn, ...(isLoading ? s.btnDisabled : {}) }}
            disabled={isLoading}
          >
            {isLoading ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <div style={s.footer}>
          Don't have an account?{" "}
          <Link to="/register" style={s.link}>
            Register
          </Link>
        </div>
      </div>
    </div>
  );
}
