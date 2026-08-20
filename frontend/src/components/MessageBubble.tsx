import type { ChatMessage } from "../types";
import { MetaBar } from "./MetaBar";

export function MessageBubble({ message }: { message: ChatMessage }) {
    const isUser = message.role === "user";
    return (
        <div className={`msg msg--${message.role}`}>
            <div className="msg__role">{isUser ? "You" : "Agent"}</div>
            <div
                className={`msg__bubble${message.error ? " msg__bubble--error" : ""}`}
            >
                {message.pending ? (
                    <span className="typing">
                        <span />
                        <span />
                        <span />
                    </span>
                ) : (
                    <p className="msg__text">{message.text}</p>
                )}
                {message.meta && !message.error && (
                    <MetaBar meta={message.meta} />
                )}
            </div>
        </div>
    );
}
