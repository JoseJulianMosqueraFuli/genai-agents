import { useMemo } from "react";
import { Chat } from "./components/Chat";
import { HealthBadge } from "./components/HealthBadge";
import { IngestPanel } from "./components/IngestPanel";

export default function App() {
    // One session per page load so multi-turn memory stays coherent server-side.
    const sessionId = useMemo(() => crypto.randomUUID(), []);

    return (
        <div className="app">
            <header className="topbar">
                <div className="topbar__brand">
                    <span className="topbar__logo">◆</span>
                    <div>
                        <h1>genai-agents</h1>
                        <p className="topbar__sub">
                            RAG · guardrails · eval · cost — on AWS Bedrock
                        </p>
                    </div>
                </div>
                <HealthBadge />
            </header>

            <main className="main">
                <IngestPanel />
                <Chat sessionId={sessionId} />
            </main>

            <footer className="footer">
                session <code>{sessionId.slice(0, 8)}</code>
            </footer>
        </div>
    );
}
