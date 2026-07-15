import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Code, Table, Loader2, Sparkles } from "lucide-react";
import clsx from "clsx";

const BASE_URL = `${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api`;

const EXAMPLE_QUESTIONS = [
  "Top 5 champion T1 pick nhiều nhất năm 2023?",
  "Faker thắng bao nhiêu trận năm 2024?",
  "Champion nào bị ban nhiều nhất trong Worlds 2023?",
  "Win rate của T1 khi chơi Blue side so với Red side?",
  "Đối thủ nào T1 gặp nhiều nhất trong lịch sử?",
];

function DataTable({ data }) {
  if (!data || data.length === 0) return null;
  const cols = Object.keys(data[0]);

  return (
    <div className="overflow-x-auto mt-3 rounded-lg border border-border">
      <table className="w-full text-xs">
        <thead className="bg-surface">
          <tr>
            {cols.map((col) => (
              <th
                key={col}
                className="px-3 py-2 text-left text-textMuted uppercase tracking-wider font-medium border-b border-border"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr
              key={i}
              className="border-b border-border/50 last:border-0 hover:bg-surfaceHover/30 transition-colors"
            >
              {cols.map((col) => (
                <td key={col} className="px-3 py-2 font-mono text-text">
                  {row[col] ?? "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SqlBlock({ sql }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="mt-2">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-1.5 text-xs text-textMuted hover:text-accent transition-colors"
      >
        <Code size={12} />
        {expanded ? "Ẩn SQL" : "Xem SQL"}
      </button>
      {expanded && (
        <pre className="mt-2 bg-bg rounded-lg px-4 py-3 text-xs text-win font-mono overflow-x-auto border border-border">
          {sql}
        </pre>
      )}
    </div>
  );
}

function Message({ msg }) {
  const isUser = msg.role === "user";

  return (
    <div className={clsx("flex gap-3", isUser && "flex-row-reverse")}>
      {/* Avatar */}
      <div
        className={clsx(
          "w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-1",
          isUser ? "bg-accent/20" : "bg-surface border border-border"
        )}
      >
        {isUser ? (
          <User size={14} className="text-accent" />
        ) : (
          <Bot size={14} className="text-textMuted" />
        )}
      </div>

      {/* Bubble */}
      <div className={clsx("max-w-[80%] space-y-1", isUser && "items-end flex flex-col")}>
        <div
          className={clsx(
            "px-4 py-3 rounded-xl text-sm leading-relaxed",
            isUser
              ? "bg-accent text-white rounded-tr-sm"
              : "bg-surface border border-border text-text rounded-tl-sm"
          )}
        >
          {msg.content}
        </div>

        {/* SQL + Table chỉ hiện với assistant message có data */}
        {!isUser && msg.sql && <SqlBlock sql={msg.sql} />}
        {!isUser && msg.data && msg.data.length > 0 && (
          <div className="w-full">
            <div className="flex items-center gap-1.5 text-xs text-textMuted mt-1 mb-1">
              <Table size={12} />
              {msg.data.length} kết quả
            </div>
            <DataTable data={msg.data} />
          </div>
        )}

        {/* Error */}
        {!isUser && msg.error && (
          <div className="text-xs text-loss bg-loss/10 border border-loss/30 rounded-lg px-3 py-2 mt-1">
            {msg.error}
          </div>
        )}
      </div>
    </div>
  );
}

export default function Agent() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Xin chào! Tôi là T1 Analytics Agent. Bạn có thể hỏi tôi bất kỳ câu hỏi nào về lịch sử thi đấu của T1 từ 2020 đến 2025.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (question) => {
    const q = question || input.trim();
    if (!q || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setLoading(true);

    try {
      const res = await fetch(`${BASE_URL}/agent/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      const data = await res.json();

      if (!res.ok) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "Có lỗi xảy ra khi xử lý câu hỏi.",
            error: data.detail || "Unknown error",
          },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: data.success
              ? "Đây là kết quả tôi tìm được:"
              : "Không thể tạo query cho câu hỏi này.",
            sql: data.sql,
            data: data.data,
            error: data.error,
          },
        ]);
      }
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Không kết nối được backend.",
          error: e.message,
        },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="mb-4">
        <h1 className="font-display font-bold text-2xl text-text tracking-tight">
          Analytics Agent
        </h1>
        <p className="text-textMuted text-sm mt-1">
          Hỏi bất kỳ câu hỏi nào về dữ liệu T1 bằng ngôn ngữ tự nhiên.
        </p>
      </div>

      {/* Example questions — chỉ hiện khi chưa có nhiều messages */}
      {messages.length <= 1 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {EXAMPLE_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => send(q)}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border border-border text-textMuted hover:border-accent hover:text-accent transition-colors bg-surface"
            >
              <Sparkles size={11} />
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-6 pr-1 pb-4">
        {messages.map((msg, i) => (
          <Message key={i} msg={msg} />
        ))}
        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-surface border border-border flex items-center justify-center shrink-0">
              <Bot size={14} className="text-textMuted" />
            </div>
            <div className="bg-surface border border-border rounded-xl rounded-tl-sm px-4 py-3">
              <Loader2 size={14} className="text-textMuted animate-spin" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-border pt-4">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
            placeholder="Hỏi về dữ liệu T1... (Enter để gửi)"
            className="flex-1 bg-surface border border-border rounded-xl px-4 py-3 text-sm text-text placeholder:text-textMuted focus:outline-none focus:border-accent transition-colors"
            disabled={loading}
          />
          <button
            onClick={() => send()}
            disabled={!input.trim() || loading}
            className="bg-accent hover:bg-accent/80 disabled:opacity-40 text-white px-4 py-3 rounded-xl transition-colors shrink-0"
          >
            <Send size={16} />
          </button>
        </div>
        <p className="text-[11px] text-textMuted mt-2 text-center">
          Agent dùng AI để tạo SQL — kết quả có thể không chính xác 100%.
        </p>
      </div>
    </div>
  );
}