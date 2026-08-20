import type { AgentResponse } from "../types";

function fmtCost(usd: number): string {
    if (usd === 0) return "$0";
    return `$${usd.toFixed(6)}`;
}

export function MetaBar({ meta }: { meta: AgentResponse }) {
    const scores = Object.entries(meta.eval_scores ?? {});
    return (
        <div className="meta">
            {meta.tier && <span className="chip chip--tier">{meta.tier}</span>}
            {meta.model && (
                <span className="chip" title="model">
                    {meta.model}
                </span>
            )}
            <span className="chip" title="latency">
                {meta.latency_ms} ms
            </span>
            <span className="chip" title="estimated cost">
                {fmtCost(meta.cost_usd)}
            </span>
            {meta.cache_hit && (
                <span className="chip chip--cache">cache hit</span>
            )}
            {scores.map(([k, v]) => (
                <span key={k} className="chip chip--score" title="eval score">
                    {k.replace("answer_", "")}: {v.toFixed(2)}
                </span>
            ))}
            {meta.context_sources?.length > 0 && (
                <span className="chip chip--src" title="retrieved sources">
                    sources: {meta.context_sources.join(", ")}
                </span>
            )}
        </div>
    );
}
