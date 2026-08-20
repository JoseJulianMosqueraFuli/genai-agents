import { useState } from "react";
import { ingest } from "../api";

export function IngestPanel() {
    const [open, setOpen] = useState(false);
    const [text, setText] = useState("");
    const [busy, setBusy] = useState(false);
    const [note, setNote] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    const submit = async () => {
        // One document per non-empty line.
        const documents = text
            .split("\n")
            .map((l) => l.trim())
            .filter(Boolean)
            .map((line) => ({ text: line }));

        if (documents.length === 0) {
            setError("Add at least one non-empty line.");
            return;
        }
        setBusy(true);
        setError(null);
        setNote(null);
        try {
            const res = await ingest(documents);
            setNote(`Ingested ${res.ingested} · index total: ${res.total}`);
            setText("");
        } catch (e) {
            setError(e instanceof Error ? e.message : "Ingest failed");
        } finally {
            setBusy(false);
        }
    };

    return (
        <section className="ingest">
            <button
                className="ingest__toggle"
                onClick={() => setOpen((v) => !v)}
            >
                {open ? "▾" : "▸"} Ingest documents (RAG)
            </button>
            {open && (
                <div className="ingest__body">
                    <p className="ingest__hint">
                        One document per line. They get embedded and stored for
                        retrieval.
                    </p>
                    <textarea
                        className="ingest__textarea"
                        rows={5}
                        placeholder={
                            "Kubernetes orchestrates containers.\nAWS Fargate runs containers without managing servers."
                        }
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                        disabled={busy}
                    />
                    <div className="ingest__actions">
                        <button
                            className="btn"
                            onClick={submit}
                            disabled={busy}
                        >
                            {busy ? "Ingesting…" : "Ingest"}
                        </button>
                        {note && <span className="ingest__note">{note}</span>}
                        {error && (
                            <span className="ingest__error">{error}</span>
                        )}
                    </div>
                </div>
            )}
        </section>
    );
}
