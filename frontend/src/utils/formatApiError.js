/**
 * Normalize FastAPI error detail to a displayable string.
 *
 * FastAPI can return:
 *   - string: "Order not found"
 *   - Pydantic 422 array: [{type, loc, msg, input}, ...]
 *   - undefined / null when the response body has no detail field
 */
export function formatApiError(detail, fallback = "An error occurred") {
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (detail instanceof Error) return detail.message;
  if (Array.isArray(detail)) {
    const msgs = detail.map((e) => e.msg ?? String(e)).filter(Boolean);
    return msgs.length > 0 ? msgs.join("; ") : fallback;
  }
  return fallback;
}
