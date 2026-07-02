import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import useAuthStore from "../store/useAuthStore";

const ROLES = ["ANALYST", "TRADER", "QUANT", "VIEWER"];

const s = {
  page: {
    minHeight: "100vh",
    background: "#0d1117",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontFamily: "'Inter', system-ui, sans-serif",
    color: "#e6edf3",
    padding: "24px 16px",
  },
  card: {
    background: "#161b22",
    border: "1px solid #30363d",
    borderRadius: 12,
    padding: "40px 36px",
    width: "100%",
    maxWidth: 440,
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
  logoName: { fontWeight: 700, fontSize: 18 },
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
  },
  select: {
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
    cursor: "pointer",
  },
  btn: {
    width: "100%",
    background: "#2563eb",
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
  success: {
    background: "#0f2a1a",
    border: "1px solid #3fb950",
    borderRadius: 6,
    color: "#3fb950",
    fontSize: 13,
    padding: "10px 14px",
    marginBottom: 16,
  },
  footer: { marginTop: 20, fontSize: 13, color: "#8b949e", textAlign: "center" },
  link: { color: "#58a6ff", textDecoration: "none" },
};

export default function Register() {
  const navigate = useNavigate();
  const { register, isLoading, error, clearError } = useAuthStore();
  const [form, setForm] = useState({ email: "", password: "", confirm: "", full_name: "", role: "ANALYST" });
  const [localError, setLocalError] = useState("");
  const [success, setSuccess] = useState(false);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLocalError("");
    clearError();

    if (form.password !== form.confirm) {
      setLocalError("Passwords do not match");
      return;
    }
    if (form.password.length < 8) {
      setLocalError("Password must be at least 8 characters");
      return;
    }

    try {
      await register(form.email.trim().toLowerCase(), form.password, form.full_name.trim(), form.role);
      setSuccess(true);
      setTimeout(() => navigate("/login", { replace: true }), 1500);
    } catch {
      // error set in store
    }
  };

  const displayError = localError || error;

  return (
    <div style={s.page}>
      <div style={s.card}>
        <div style={s.logo}>
          <div style={s.logoQ}>Q</div>
          <span style={s.logoName}>QuantLab AI</span>
        </div>

        <h1 style={s.title}>Create account</h1>
        <p style={s.subtitle}>Join the institutional trading platform</p>

        {displayError && <div style={s.error}>{displayError}</div>}
        {success && <div style={s.success}>Account created! Redirecting to login…</div>}

        <form onSubmit={handleSubmit}>
          <label style={s.label}>Full name</label>
          <input
            type="text"
            style={s.input}
            value={form.full_name}
            onChange={(e) => set("full_name", e.target.value)}
            placeholder="Jane Smith"
            autoFocus
          />

          <label style={s.label}>Email address</label>
          <input
            type="email"
            style={s.input}
            value={form.email}
            onChange={(e) => set("email", e.target.value)}
            placeholder="analyst@example.com"
            required
            autoComplete="email"
          />

          <label style={s.label}>Role</label>
          <select
            style={s.select}
            value={form.role}
            onChange={(e) => set("role", e.target.value)}
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>

          <label style={s.label}>Password</label>
          <input
            type="password"
            style={s.input}
            value={form.password}
            onChange={(e) => set("password", e.target.value)}
            placeholder="At least 8 characters"
            required
            autoComplete="new-password"
          />

          <label style={s.label}>Confirm password</label>
          <input
            type="password"
            style={s.input}
            value={form.confirm}
            onChange={(e) => set("confirm", e.target.value)}
            placeholder="Repeat password"
            required
            autoComplete="new-password"
          />

          <button
            type="submit"
            style={{ ...s.btn, ...(isLoading || success ? s.btnDisabled : {}) }}
            disabled={isLoading || success}
          >
            {isLoading ? "Creating account…" : "Create account"}
          </button>
        </form>

        <div style={s.footer}>
          Already have an account?{" "}
          <Link to="/login" style={s.link}>
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
}
