import type { AgentResponse, Health, IngestResponse } from "./types";

// Empty base => same-origin (dev proxy handles /v1 and /health). Set VITE_API_BASE
// for a built SPA served from a different origin than the API.
const BASE = (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(`${BASE}${path}`, {
        headers: { "Content-Type": "application/json" },
        ...init,
    });
    if (!res.ok) {
        let detail = `${res.status} ${res.statusText}`;
        try {
            const body = await res.json();
            if (body?.detail)
                detail =
                    typeof body.detail === "string"
                        ? body.detail
                        : JSON.stringify(body.detail);
        } catch {
            // non-JSON error body; keep the status line
        }
        throw new Error(detail);
    }
    return res.json() as Promise<T>;
}

export function chat(
    query: string,
    sessionId: string,
    useRag = true,
): Promise<AgentResponse> {
    return request<AgentResponse>("/v1/agents/chat", {
        method: "POST",
        body: JSON.stringify({ query, session_id: sessionId, use_rag: useRag }),
    });
}

export function ingest(
    documents: { text: string; metadata?: Record<string, unknown> }[],
): Promise<IngestResponse> {
    return request<IngestResponse>("/v1/documents", {
        method: "POST",
        body: JSON.stringify({ documents }),
    });
}

export function health(): Promise<Health> {
    return request<Health>("/health");
}
