import { useState } from "react";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LANGUAGES, languageAfterToggle, setLanguage } from "@/lib/translate";

interface Props {
  selected: string[];
  onChange: (codes: string[]) => void;
}

/** Searchable language checklist; ticking a language also switches the app into it. */
export default function LanguageChecklist({ selected, onChange }: Props) {
  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase();
  const shown = LANGUAGES.filter((l) => !q || l.name.toLowerCase().includes(q) || l.native.toLowerCase().includes(q));

  const toggle = (code: string) => {
    const next = selected.includes(code) ? selected.filter((c) => c !== code) : [...selected, code];
    onChange(next);
    setLanguage(languageAfterToggle(next, code));
  };

  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="languageSearch" className="text-sm font-medium">Search Languages</Label>
        <div className="relative mt-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <Input id="languageSearch" type="text" placeholder="Search for languages..." value={query}
                 onChange={(e) => setQuery(e.target.value)}
                 className="pl-10 border-green-300 focus:border-green-500 focus:ring-green-500" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto border border-green-200 rounded-lg p-3">
        {shown.map((l) => (
          <label key={l.code} className="flex items-center space-x-2 p-2 hover:bg-green-100 rounded cursor-pointer" translate="no">
            <input type="checkbox" checked={selected.includes(l.code)} onChange={() => toggle(l.code)}
                   className="border-green-500 text-green-600 focus:ring-green-500" />
            <span className="text-sm">{l.flag} {l.name} <span className="text-muted-foreground">{l.native !== l.name ? l.native : ""}</span></span>
          </label>
        ))}
        {shown.length === 0 && <p className="text-sm text-muted-foreground col-span-2">No language matches "{query}".</p>}
      </div>
      <p className="text-xs text-muted-foreground">The app switches to the language you tick last.</p>
    </div>
  );
}
