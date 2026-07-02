import { useState } from "react";
import { Link } from "react-router-dom";

const modules = [
  {
    title: "Regime Detection",
    description: "Detect BULL / BEAR / HIGH_VOL / LOW_VOL / RANGING regimes via MA crossover, momentum, and realized volatility.",
    to: "/m20/regime",
    color: "#6366f1",
  },
  {
    title: "Correlation & Covariance",
    description: "Compute N×N Pearson correlation matrices, rolling correlation, and asset cluster detection.",
    to: "/m20/correlation",
    color: "#0ea5e9",
  },
  {
    title: "Strategy Comparison",
    description: "Rank multiple backtested strategies by Sharpe, Sortino, Calmar. Head-to-head analysis and equity-curve correlation.",
    to: "/m20/comparison",
    color: "#10b981",
  },
];

export default function M20Dashboard() {
  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "2rem 1rem" }}>
      <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "0.5rem" }}>
        M20 — Quant Research Platform Closeout
      </h1>
      <p style={{ color: "#94a3b8", marginBottom: "2rem", fontSize: "0.95rem" }}>
        Final milestone of the QuantLab AI Quant Research block. Pure-Python regime detection,
        correlation analysis, and multi-strategy ranking.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "1.25rem" }}>
        {modules.map((mod) => (
          <Link
            key={mod.to}
            to={mod.to}
            style={{ textDecoration: "none" }}
          >
            <div
              style={{
                border: "1px solid #1e293b",
                borderRadius: 10,
                padding: "1.5rem",
                background: "#0f172a",
                transition: "border-color 0.15s",
                cursor: "pointer",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = mod.color)}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = "#1e293b")}
            >
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 8,
                  background: mod.color + "22",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: "0.75rem",
                }}
              >
                <span style={{ color: mod.color, fontWeight: 700, fontSize: "1.1rem" }}>M20</span>
              </div>
              <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.4rem", color: "#f1f5f9" }}>
                {mod.title}
              </h3>
              <p style={{ fontSize: "0.85rem", color: "#64748b", lineHeight: 1.5 }}>{mod.description}</p>
            </div>
          </Link>
        ))}
      </div>

      <div
        style={{
          marginTop: "2.5rem",
          padding: "1.25rem",
          background: "#0f172a",
          border: "1px solid #1e293b",
          borderRadius: 8,
          fontSize: "0.85rem",
          color: "#64748b",
        }}
      >
        <strong style={{ color: "#94a3b8" }}>Stack:</strong> Python 3.14 · FastAPI · Pydantic v2 · Pure-Python linear algebra ·
        No scipy / numpy / pandas / TA-Lib · Docker only
      </div>
    </div>
  );
}
