import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";

export type UpdateBannerProps = {
  message: string | null;
  onClose: () => void;
  timeoutMs?: number;
};

export function UpdateBanner({ message, onClose, timeoutMs = 5000 }: UpdateBannerProps) {
  useEffect(() => {
    if (!message) return;
    const t = setTimeout(onClose, timeoutMs);
    return () => clearTimeout(t);
  }, [message, onClose, timeoutMs]);

  return (
    <AnimatePresence>
      {message && (
        <motion.div
          initial={{ y: -16, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -16, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed top-3 left-1/2 -translate-x-1/2 z-50"
        >
          <div className="bg-primary text-primary-foreground shadow-lg rounded-full px-4 py-2 flex items-center gap-2">
            <span className="text-sm">{message}</span>
            <button onClick={onClose} className="opacity-80 hover:opacity-100">
              <X size={16} />
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
