import { FormEvent, useEffect, useRef, useState } from "react";
import { Send, Bot } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, currentPosition, Place, Proposal, Trip } from "@/lib/livetrip";
import { currentLanguage } from "@/lib/translate";
import ProposalDialog from "./ProposalDialog";
import PlaceList from "./PlaceList";

interface Message {
  role: "user" | "assistant";
  text: string;
  places?: Place[];
  proposal?: Proposal;
}

const EXAMPLES = [
  "What should I visit next?",
  "Find a vegetarian restaurant nearby",
  "Replace my next activity with an indoor attraction",
  "Make the rest of my day more relaxed",
  "I have only two hours left",
];

interface Props {
  tripId?: string | number | null;
  onTripChanged?: (trip: Trip) => void;
  className?: string;
}

export default function AssistantPanel({ tripId, onTripChanged, className = "h-[28rem]" }: Props) {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", text: "Hi! Ask me to find places, change your plan, or suggest what to do next." },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [useLocation, setUseLocation] = useState(false);
  const [pending, setPending] = useState<Proposal | null>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  const send = async (text: string) => {
    if (!text.trim()) return;
    // the conversation so far gives the assistant context ("and vegetarian?", "tell me more about it")
    const history = messages.slice(1).slice(-12).map(({ role, text }) => ({ role, text: text.slice(0, 2000) }));
    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    setBusy(true);
    try {
      const pos = useLocation ? await currentPosition() : null;
      const res = await api<{ reply: string; places?: Place[]; proposal?: Proposal }>("/api/assistant/message", {
        method: "POST",
        json: { message: text, trip_id: tripId ? Number(tripId) : null, history, page: window.location.pathname,
                language: currentLanguage(), ...(pos ?? {}) },
      });
      setMessages((m) => [...m, { role: "assistant", text: res.reply, places: res.places, proposal: res.proposal }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", text: `Sorry, that failed: ${(e as Error).message}` }]);
    } finally {
      setBusy(false);
    }
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    send(input);
  };

  return (
    <div className={`flex flex-col ${className}`}>
      <div className="flex-1 overflow-y-auto space-y-3 pr-1">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[90%] rounded-lg px-3 py-2 text-sm whitespace-pre-line ${m.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"}`}>
              {m.role === "assistant" && <Bot className="w-4 h-4 inline mr-1 -mt-0.5" />}
              {m.text}
              {m.places && m.places.length > 0 && !m.proposal && (
                <div className="mt-2 bg-background rounded p-2 text-foreground"><PlaceList places={m.places.slice(0, 5)} /></div>
              )}
              {m.proposal && tripId && (
                <Button size="sm" className="mt-2" onClick={() => setPending(m.proposal!)}>Review and confirm</Button>
              )}
            </div>
          </div>
        ))}
        {busy && (
          <div className="flex justify-start" role="status" aria-label="Assistant is typing">
            <div className="rounded-lg px-3 py-2 bg-muted flex items-center gap-1">
              <Bot className="w-4 h-4 mr-1" />
              {[0, 150, 300].map((d) => (
                <span key={d} className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: `${d}ms` }} />
              ))}
            </div>
          </div>
        )}
        <div ref={end} />
      </div>
      <div className="flex flex-wrap gap-1 my-2">
        {EXAMPLES.map((e) => (
          <button key={e} type="button" onClick={() => send(e)} disabled={busy}
                  className="text-xs rounded-full border px-2 py-0.5 hover:bg-muted">{e}</button>
        ))}
      </div>
      <label className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
        <input type="checkbox" checked={useLocation} onChange={(e) => setUseLocation(e.target.checked)} />
        Use my current location for nearby suggestions
      </label>
      <form onSubmit={submit} className="flex gap-2">
        <Input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask LiveTrip..." disabled={busy} />
        <Button type="submit" disabled={busy || !input.trim()} aria-label="Send"><Send className="w-4 h-4" /></Button>
      </form>
      {tripId && (
        <ProposalDialog tripId={tripId} proposal={pending} onClose={() => setPending(null)}
                        onApplied={(t) => onTripChanged?.(t)} />
      )}
    </div>
  );
}
