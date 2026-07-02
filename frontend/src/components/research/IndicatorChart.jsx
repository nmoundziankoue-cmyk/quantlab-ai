/**
 * IndicatorChart
 *
 * Renders OHLCV candlesticks on a primary pane using lightweight-charts v4,
 * with optional indicator overlays on the same pane (SMA, EMA, BB) and a
 * sub-pane for momentum oscillators (RSI, MACD histogram, Stochastic).
 */

import { useEffect, useRef } from "react";
import { createChart, CrosshairMode } from "lightweight-charts";

const CHART_COLORS = {
  sma: ["#60a5fa", "#f59e0b", "#34d399", "#a78bfa"],
  ema: ["#818cf8", "#fb923c"],
  bbands: "#94a3b8",
  rsi: "#f472b6",
  macd: "#3b82f6",
  signal: "#f97316",
  hist_pos: "#22c55e",
  hist_neg: "#ef4444",
};

function extractSmaEmaOverlays(indicators) {
  const overlays = [];
  let smaPaletteIdx = 0;
  let emaPaletteIdx = 0;

  Object.entries(indicators).forEach(([key, data]) => {
    if (key.startsWith("sma_") && Array.isArray(data)) {
      overlays.push({ key, color: CHART_COLORS.sma[smaPaletteIdx++ % 4], data });
    }
    if (key.startsWith("ema_") && Array.isArray(data)) {
      overlays.push({ key, color: CHART_COLORS.ema[emaPaletteIdx++ % 2], data });
    }
    if (key.startsWith("wma_") && Array.isArray(data)) {
      overlays.push({ key, color: "#a78bfa", data });
    }
  });

  return overlays;
}

function buildLineSeries(chart, times, values, color, title) {
  const series = chart.addLineSeries({
    color,
    lineWidth: 1.5,
    title,
    priceLineVisible: false,
    lastValueVisible: false,
  });
  const pts = times
    .map((t, i) => (values[i] !== null ? { time: t, value: values[i] } : null))
    .filter(Boolean);
  series.setData(pts);
  return series;
}

export default function IndicatorChart({ ohlcv = [], indicators = {}, height = 420 }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const subChartRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || !ohlcv.length) return;

    const container = containerRef.current;
    container.innerHTML = "";

    const times = ohlcv.map((b) => b.time);

    // Decide if we need a sub-pane (oscillator indicators)
    const hasRsi = Object.keys(indicators).some((k) => k.startsWith("rsi_"));
    const hasMacd = "macd" in indicators || Object.keys(indicators).some((k) => k.startsWith("macd_"));
    const hasStoch = Object.keys(indicators).some((k) => k.startsWith("stoch_"));
    const hasSubPane = hasRsi || hasMacd || hasStoch;

    const mainHeight = hasSubPane ? Math.round(height * 0.65) : height;
    const subHeight = height - mainHeight;

    // ---------- main chart ----------
    const mainDiv = document.createElement("div");
    mainDiv.style.height = mainHeight + "px";
    container.appendChild(mainDiv);

    const chart = createChart(mainDiv, {
      width: container.clientWidth,
      height: mainHeight,
      layout: {
        background: { color: "#080c14" },
        textColor: "#64748b",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "#0f1520" },
        horzLines: { color: "#0f1520" },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: "#1e2230" },
      timeScale: {
        borderColor: "#1e2230",
        timeVisible: true,
        secondsVisible: false,
      },
    });
    chartRef.current = chart;

    // Candlestick series
    const candles = chart.addCandlestickSeries({
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderUpColor: "#22c55e",
      borderDownColor: "#ef4444",
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
    });
    candles.setData(
      ohlcv.map((b) => ({
        time: b.time,
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      }))
    );

    // Bollinger Bands overlay
    Object.entries(indicators).forEach(([key, data]) => {
      if (key.startsWith("bbands_") && typeof data === "object" && !Array.isArray(data)) {
        const { upper, middle, lower } = data;
        buildLineSeries(chart, times, upper, CHART_COLORS.bbands, "BB Upper");
        buildLineSeries(chart, times, middle, "#475569", "BB Mid");
        buildLineSeries(chart, times, lower, CHART_COLORS.bbands, "BB Lower");
      }
    });

    // SMA / EMA / WMA overlays
    extractSmaEmaOverlays(indicators).forEach(({ key, color, data }) => {
      buildLineSeries(chart, times, data, color, key.toUpperCase().replace("_", " "));
    });

    chart.timeScale().fitContent();

    // ---------- sub-pane (oscillators) ----------
    if (hasSubPane) {
      const subDiv = document.createElement("div");
      subDiv.style.height = subHeight + "px";
      subDiv.style.marginTop = "2px";
      container.appendChild(subDiv);

      const subChart = createChart(subDiv, {
        width: container.clientWidth,
        height: subHeight,
        layout: {
          background: { color: "#080c14" },
          textColor: "#64748b",
          fontSize: 11,
        },
        grid: {
          vertLines: { color: "#0f1520" },
          horzLines: { color: "#0f1520" },
        },
        crosshair: { mode: CrosshairMode.Normal },
        rightPriceScale: { borderColor: "#1e2230" },
        timeScale: {
          borderColor: "#1e2230",
          timeVisible: true,
          secondsVisible: false,
        },
      });
      subChartRef.current = subChart;

      if (hasRsi) {
        const rsiKey = Object.keys(indicators).find((k) => k.startsWith("rsi_"));
        if (rsiKey) {
          buildLineSeries(subChart, times, indicators[rsiKey], CHART_COLORS.rsi, rsiKey.toUpperCase().replace("_", " "));
          // Overbought/oversold reference lines
          [70, 30].forEach((level) => {
            const ref = subChart.addLineSeries({
              color: "#334155",
              lineWidth: 1,
              lineStyle: 1, // dashed
              priceLineVisible: false,
              lastValueVisible: false,
            });
            ref.setData([
              { time: times[0], value: level },
              { time: times[times.length - 1], value: level },
            ]);
          });
        }
      } else if (hasMacd) {
        const macdKey =
          Object.keys(indicators).find((k) => k === "macd") ||
          Object.keys(indicators).find((k) => k.startsWith("macd_"));
        if (macdKey) {
          const { macd: macdLine, signal, hist } = indicators[macdKey];
          buildLineSeries(subChart, times, macdLine, CHART_COLORS.macd, "MACD");
          buildLineSeries(subChart, times, signal, CHART_COLORS.signal, "Signal");
          // Histogram as bars
          const histSeries = subChart.addHistogramSeries({
            priceLineVisible: false,
            lastValueVisible: false,
          });
          histSeries.setData(
            times
              .map((t, i) =>
                hist[i] !== null
                  ? {
                      time: t,
                      value: hist[i],
                      color: hist[i] >= 0 ? CHART_COLORS.hist_pos : CHART_COLORS.hist_neg,
                    }
                  : null
              )
              .filter(Boolean)
          );
        }
      } else if (hasStoch) {
        const stochKey = Object.keys(indicators).find((k) => k.startsWith("stoch_"));
        if (stochKey) {
          const { "%K": k, "%D": d } = indicators[stochKey];
          buildLineSeries(subChart, times, k, "#60a5fa", "%K");
          buildLineSeries(subChart, times, d, "#f97316", "%D");
        }
      }

      subChart.timeScale().fitContent();

      // Synchronise scrolling between main and sub chart
      chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
        if (range) subChart.timeScale().setVisibleLogicalRange(range);
      });
      subChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
        if (range) chart.timeScale().setVisibleLogicalRange(range);
      });
    }

    // Responsive resize
    const ro = new ResizeObserver(() => {
      chart.applyOptions({ width: container.clientWidth });
      if (subChartRef.current) {
        subChartRef.current.applyOptions({ width: container.clientWidth });
      }
    });
    ro.observe(container);

    return () => {
      ro.disconnect();
      chart.remove();
      if (subChartRef.current) subChartRef.current.remove();
      chartRef.current = null;
      subChartRef.current = null;
    };
  }, [ohlcv, indicators, height]);

  return <div ref={containerRef} style={{ width: "100%", height }} />;
}
