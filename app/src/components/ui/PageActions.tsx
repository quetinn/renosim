import { Check, Link2, Printer } from "lucide-react";
import { useEffect, useState } from "react";
import { useAppState } from "../../state/AppState";
import { Button } from "./Button";

/**
 * "Partager" + "Imprimer" actions for the results and scenarios screens.
 * The share link embeds the whole description in the URL fragment (never sent
 * to any server); printing relies on the print stylesheet in index.css.
 */
export function PageActions() {
  const { shareUrl } = useAppState();
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(false), 2500);
    return () => window.clearTimeout(timer);
  }, [copied]);

  const copyLink = async () => {
    const url = shareUrl();
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
    } catch {
      // Clipboard unavailable (http, old browser): let the user copy manually.
      window.prompt("Copiez ce lien de partage :", url);
    }
  };

  return (
    <div className="flex items-center gap-1 print:hidden">
      <Button variant="ghost" onClick={() => void copyLink()}>
        {copied ? <Check size={16} aria-hidden /> : <Link2 size={16} aria-hidden />}
        {copied ? "Lien copié !" : "Partager"}
      </Button>
      <Button
        variant="ghost"
        onClick={() => window.print()}
        title="Pour un export PDF : choisissez « Enregistrer en PDF » comme imprimante."
      >
        <Printer size={16} aria-hidden />
        Imprimer / PDF
      </Button>
    </div>
  );
}
