import { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { canPromptInstall, isInstalled, isIos, onInstallChange, promptInstall } from "@/lib/pwa";

/** "Install app" in the navbar: only shown where installing is possible and it isn't installed already. */
export default function InstallAppButton({ tile = false }: { tile?: boolean }) {
  const { toast } = useToast();
  const [promptable, setPromptable] = useState(canPromptInstall());
  useEffect(() => onInstallChange(() => setPromptable(canPromptInstall())), []);

  const ios = isIos();
  if (isInstalled() || (!promptable && !ios)) return null;

  return (
    <button type="button" title="Install app" aria-label="Install the LiveTrip app" data-buddy="install"
            className={tile
              ? "flex flex-col items-center gap-2 rounded-2xl p-3 text-center text-xs font-medium hover:bg-accent"
              : "text-foreground hover:text-primary transition-colors duration-200 hover:scale-110"}
            onClick={() => (ios
              ? toast({ title: "Install LiveTrip", description: "In Safari, tap Share, then Add to Home Screen." })
              : promptInstall())}>
      <Download className={tile ? "w-6 h-6 text-primary" : "w-5 h-5"} />
      {tile && "Install app"}
    </button>
  );
}
