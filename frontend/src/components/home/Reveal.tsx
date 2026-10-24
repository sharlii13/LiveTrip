import { ReactNode } from "react";
import { motion, useReducedMotion } from "framer-motion";

/** Slides its content up into view the first time it scrolls onto the screen. */
export default function Reveal({ children, delay = 0, className }: { children: ReactNode; delay?: number; className?: string }) {
  const calm = useReducedMotion();
  return (
    <motion.div className={className} initial={calm ? false : { opacity: 0, y: 60 }} whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.2 }} transition={{ duration: 0.7, delay, ease: [0.22, 1, 0.36, 1] }}>
      {children}
    </motion.div>
  );
}
