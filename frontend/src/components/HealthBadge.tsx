import { useEffect, useState } from "react";
import { health } from "../api";
import type { Health } from "../types";

type Status = "ok" | "down" | "loading";

export function HealthBadge() {
    const [status, setStatus] = useState<Status>("loading");
    const [info, setInfo] = useState<Health | null>(null);

    useEffect(() => {
        let alive = true;
        const check = async () => {
            try {
                const h = await health();
                if (!alive) return;
                setInfo(h);
                setStatus("ok");
            } catch {
                if (!alive) return;
                setStatus("down");
            }
        };
        check();
        const id = setInterval(check, 15000);
        return () => {
            alive = false;
            clearInterval(id);
        };
    }, []);

    const label =
        status === "ok" && info
            ? `${info.provider} · memory:${info.memory_backend} · guardrails:${info.guardrails ? "on" : "off"}`
            : status === "down"
              ? "API unreachable"
              : "checking…";

    return (
        <div className={`health health--${status}`} title={label}>
            <span className="health__dot" />
            <span className="health__label">{label}</span>
        </div>
    );
}
