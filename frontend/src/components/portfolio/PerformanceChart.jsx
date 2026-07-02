import { useEffect, useRef } from "react";
import { createChart, ColorType, LineStyle } from "lightweight-charts";

export default function PerformanceChart({ navSeries = [], benchmark = "SPY", height = 320 }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#0d0f14" },
        textColor: "#64748b",
      },
      grid: {
        vertLines: { color: "#111623" },
        horzLines: { color: "#111623" },
      },
      crosshair: { mode: 1 },
      rightPriceScale: { borderColor: "#1e2230" },
      timeScale: { borderColor: "#1e2230", timeVisible: true },
      width: containerRef.current.clientWidth,
      height,
    });

    chartRef.current = chart;

    const portfolioSeries = chart.addLineSeries({
      color: "#3b82f6",
      lineWidth: 2,
      title: "Portfolio",
    });

    const benchmarkSeries = chart.addLineSeries({
      color: "#64748b",
      lineWidth: 1.5,
      lineStyle: LineStyle.Dashed,
      title: benchmark,
    });

    if (navSeries.length > 0) {
      portfolioSeries.setData(
        navSeries.map((p) => ({ time: p.date, value: p.nav }))
      );

      const bmarkData = navSeries
        .filter((p) => p.benchmark_nav != null)
        .map((p) => ({ time: p.date, value: p.benchmark_nav }));
      if (bmarkData.length) benchmarkSeries.setData(bmarkData);

      chart.timeScale().fitContent();
    }

    const ro = new ResizeObserver(() => {
      if (containerRef.current)
        chart.applyOptions({ width: containerRef.current.clientWidth });
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
    };
  }, [navSeries, benchmark, height]);

  if (navSeries.length === 0)
    return <div style={styles.empty}>No performance data yet — add a DEPOSIT and some BUY transactions.</div>;

  return (
    <div style={{ ...styles.wrapper, height }}>
      <div ref={containerRef} style={{ width: "100%", height }} />
    </div>
  );
}

const styles = {
  wrapper: { borderRadius: 8, overflow: "hidden" },
  empty: { color: "#475569", fontSize: 13, padding: "40px 16px", textAlign: "center" },
};
