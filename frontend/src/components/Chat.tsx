import { useEffect, useRef, useState } from "react";
import { chat } from "../api";
import type { ChatMessage } from "../types";
import { MessageBubble } from "./MessageBubble";

function newId(): string {
    return crypto.randomUUID();
}

export function Chat({ sessionId }: { sessionId: string }) {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState("");
    const [useRag, setUseRag] = useState(true);
    const [busy, setBusy] = useState(false);
    const listRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        listRef.current?.scrollTo({
            top: listRef.current.scrollHeight,
            behavior: "smooth",
        });
    }, [messages]);

    const send = async () => {
        const query = input.trim();
        if (!query || busy) return;

        const userMsg: ChatMessage = { id: newId(), role: "user", text: query };
        const pendingId = newId();
        const pendingMsg: ChatMessage = {
            id: pendingId,
            role: "assistant",
            text: "",
            pending: true,
        };

        setMessages((prev) => [...prev, userMsg, pendingMsg]);
        setInput("");
        setBusy(true);

        try {
            const res = await chat(query, sessionId, useRag);
            setMessages((prev) =>
                prev.map((m) =>
                    m.id === pendingId
                        ? { ...m, text: res.answer, meta: res, pending: false }
                        : m,
                ),
            );
        } catch (e) {
            const detail = e instanceof Error ? e.message : "Request failed";
            setMessages((prev) =>
                prev.map((m) =>
                    m.id === pendingId
                        ? {
                              ...m,
                              text: `Error: ${detail}`,
                              error: true,
                              pending: false,
                          }
                        : m,
                ),
            );
        } finally {
            setBusy(false);
        }
    };

    const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            void send();
        }
    };

    return (
        <div className="chat">
            <div className="chat__list" ref={listRef}>
                {messages.length === 0 && (
                    <div className="chat__empty">
                        <p>
                            Ask a question. Ground answers by ingesting
                            documents first (panel above).
                        </p>
                    </div>
                )}
                {messages.map((m) => (
                    <MessageBubble key={m.id} message={m} />
                ))}
            </div>

            <div className="composer">
                <label
                    className="composer__rag"
                    title="Use retrieval-augmented generation"
                >
                    <input
                        type="checkbox"
                        checked={useRag}
                        onChange={(e) => setUseRag(e.target.checked)}
                    />
                    RAG
                </label>
                <textarea
                    className="composer__input"
                    rows={1}
                    placeholder="Ask something… (Enter to send, Shift+Enter for newline)"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={onKeyDown}
                    disabled={busy}
                />
                <button
                    className="btn btn--send"
                    onClick={send}
                    disabled={busy || !input.trim()}
                >
                    Send
                </button>
            </div>
        </div>
    );
}
