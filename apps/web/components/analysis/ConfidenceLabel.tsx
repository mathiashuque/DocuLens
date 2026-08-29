/**
 * Confidence is a heuristic model estimate, never a calibrated probability
 * or an accuracy guarantee. The label says so explicitly rather than
 * presenting a bare, implicitly-authoritative percentage.
 */
export function ConfidenceLabel({ confidence }: { confidence: number }) {
  const percent = Math.round(confidence * 100);
  return (
    <span
      className="text-xs text-zinc-500"
      title="Heuristic model confidence, not a calibrated probability of correctness."
    >
      Confidence: {percent}% (model estimate)
    </span>
  );
}
