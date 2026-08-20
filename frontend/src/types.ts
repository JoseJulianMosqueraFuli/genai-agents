// Mirrors the FastAPI response models in app/main.py.

export interface Usage {
    input_tokens?: number;
    output_tokens?: number;
}

export interface AgentResponse {
    query: string;
    answer: string;
    provider: string;
    model: string;
    session_id: string;
    context_sources: string[];
    eval_scores: Record<string, number>;
    usage: Usage;
    cost_usd: number;
    guardrail_blocked: boolean;
    latency_ms: number;
    cache_hit: boolean;
    tier: string;
}

export interface IngestResponse {
    ingested: number;
    total: number;
}

export interface Health {
    status: string;
    app: string;
    provider: string;
    guardrails: boolean;
    memory_backend: string;
}

export type Role = "user" | "assistant";

export interface ChatMessage {
    id: string;
    role: Role;
    text: string;
    // Present on assistant messages once the response arrives.
    meta?: AgentResponse;
    error?: boolean;
    pending?: boolean;
}
