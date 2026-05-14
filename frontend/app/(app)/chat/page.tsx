"use client";

import { useState, useRef, useEffect, useCallback, type ReactNode } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";
import { Send, Bot, User, Lightbulb, Loader, ShieldCheck } from "lucide-react";

const SUGGESTED_QUERIES = [
  "What's my cash runway?",
  "Summarize my biggest expenses",
  "Compare this month to last month",
  "Should I be worried about my burn rate?",
  "Which budget categories am I overspending?",
];

const SECTION_LINE_RE = /^[A-Za-z][A-Za-z /&()'-]*:$/;

function renderInlineFormatting(text: string): ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);

  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={index} className="font-semibold">
          {part.slice(2, -2)}
        </strong>
      );
    }

    return <span key={index}>{part}</span>;
  });
}

function renderAssistantContent(content: string) {
  const lines = content.split("\n");

  return (
    <div className="space-y-2">
      {lines.map((line, index) => {
        const trimmed = line.trim();
        if (!trimmed) {
          return <div key={index} className="h-1.5" />;
        }

        const bulletMatch = trimmed.match(/^[-•]\s+(.*)$/);
        if (bulletMatch) {
          return (
            <div key={index} className="flex gap-2 pl-1">
              <span className="mt-[1px] shrink-0 font-semibold" style={{ color: "var(--accent)" }}>
                •
              </span>
              <span className="flex-1">{renderInlineFormatting(bulletMatch[1])}</span>
            </div>
          );
        }

        if (SECTION_LINE_RE.test(trimmed)) {
          return (
            <div
              key={index}
              className="text-[11px] font-semibold uppercase tracking-[0.18em]"
              style={{ color: "var(--accent)" }}
            >
              {trimmed.slice(0, -1)}
            </div>
          );
        }

        return (
          <p key={index} className="whitespace-pre-wrap">
            {renderInlineFormatting(line)}
          </p>
        );
      })}
    </div>
  );
}

export default function ChatPage() {
  const { getToken } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "Hello! I'm your AI CFO assistant. Ask me anything about your finances — cash flow, budgets, forecasts, or spending patterns.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [suggestedActions, setSuggestedActions] = useState<string[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || loading) return;

      setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
      setInput("");
      setSuggestedActions([]);
      setLoading(true);

      try {
        const token = await getToken();
        const res = await api.sendChat(trimmed, token);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: res.reply },
        ]);
        if (res.suggested_actions?.length > 0) {
          setSuggestedActions(res.suggested_actions);
        }
      } catch {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content:
              "I'm having trouble reaching the server right now. Please check your connection and try again.",
          },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [loading, getToken]
  );

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  };

  return (
    <div
      className="max-w-3xl mx-auto flex flex-col animate-fade-up"
      style={{ height: "calc(100vh - 64px)" }}
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-6 shrink-0">
        <div
          className="flex items-center justify-center"
          style={{ width: 40, height: 40, borderRadius: 12, background: "var(--accent-soft)" }}
        >
          <Bot size={20} style={{ color: "var(--accent)" }} />
        </div>
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>AI CFO Chat</h1>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>Ask anything about your finances</p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1 mb-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"} animate-fade-up`}
          >
            {msg.role === "assistant" && (
              <div className="shrink-0 flex items-center justify-center mt-1" style={{ width: 28, height: 28, borderRadius: 8, background: "var(--accent-soft)" }}>
                <Bot size={14} style={{ color: "var(--accent)" }} />
              </div>
            )}

            <div className="max-w-[80%]">
              <div
                className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                  msg.role === "user" ? "whitespace-pre-wrap" : ""
                }`}
                style={
                  msg.role === "user"
                    ? { background: "var(--accent)", color: "#fff", borderBottomRightRadius: 4 }
                    : { background: "var(--glass-bg)", border: "1px solid var(--border)", color: "var(--text)", borderBottomLeftRadius: 4 }
                }
              >
                {msg.role === "assistant" ? renderAssistantContent(msg.content) : msg.content}
              </div>
              {msg.role === "assistant" && i > 0 && (
                <div className="flex items-center gap-1 mt-1 ml-1" style={{ color: "var(--text-muted)", fontSize: 10 }}>
                  <ShieldCheck size={10} />
                  AI-generated · may contain inaccuracies · verify before acting
                </div>
              )}
            </div>

            {msg.role === "user" && (
              <div className="shrink-0 flex items-center justify-center mt-1" style={{ width: 28, height: 28, borderRadius: 8, background: "var(--accent-soft)" }}>
                <User size={14} style={{ color: "var(--accent)" }} />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex gap-3 justify-start animate-fade-up">
            <div className="shrink-0 flex items-center justify-center" style={{ width: 28, height: 28, borderRadius: 8, background: "var(--accent-soft)" }}>
              <Bot size={14} style={{ color: "var(--accent)" }} />
            </div>
            <div className="px-4 py-3 rounded-2xl text-sm flex items-center gap-2" style={{ background: "var(--glass-bg)", border: "1px solid var(--border)", color: "var(--text-muted)", borderBottomLeftRadius: 4 }}>
              <Loader size={14} className="animate-spin" /> Thinking…
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Suggested actions */}
      {suggestedActions.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3 shrink-0">
          <Lightbulb size={14} style={{ color: "var(--accent)", marginTop: 2 }} />
          {suggestedActions.map((action, i) => (
            <button key={i} onClick={() => send(action)} className="text-xs px-3 py-1.5 rounded-full transition-all" style={{ background: "var(--accent-soft)", color: "var(--accent)", border: "1px solid var(--accent)" }}>
              {action}
            </button>
          ))}
        </div>
      )}

      {/* Suggested Queries (initial) */}
      {messages.length === 1 && !loading && (
        <div className="flex flex-wrap gap-2 mb-3 shrink-0">
          {SUGGESTED_QUERIES.map((q, i) => (
            <button key={i} onClick={() => send(q)} className="text-xs px-3 py-1.5 rounded-full transition-all" style={{ background: "var(--glass-bg)", color: "var(--text-muted)", border: "1px solid var(--border)" }}>
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="glass flex items-end gap-3 p-3 shrink-0" style={{ borderRadius: 16 }}>
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask about your finances… (Enter to send, Shift+Enter for newline)"
          rows={1}
          className="flex-1 resize-none text-sm bg-transparent outline-none"
          style={{ color: "var(--text)", minHeight: 36, maxHeight: 120 }}
        />
        <button
          onClick={() => send(input)}
          disabled={loading || !input.trim()}
          className="btn-primary flex items-center gap-2 shrink-0 py-2 px-4"
          style={{ opacity: !input.trim() || loading ? 0.5 : 1 }}
        >
          <Send size={14} /> Send
        </button>
      </div>
    </div>
  );
}
