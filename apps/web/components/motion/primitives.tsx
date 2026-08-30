"use client";

import { motion, useReducedMotion, type Variants } from "motion/react";
import type { ReactNode } from "react";

/**
 * The app's entire animation vocabulary lives here: a mount-only entrance
 * (`Reveal`) and a small stagger pair (`StaggerGroup`/`StaggerItem`) for the
 * short, fixed-size card sets called out in the design brief (hero, demo
 * cards, analysis sections). Nothing here uses `AnimatePresence`/`exit`: all
 * of these wrap content that is added, never content that is swapped in
 * place, so there is no interval where old and new content coexist for a
 * test (or a screen reader) to observe.
 */

const EASE = [0.16, 1, 0.3, 1] as const;
const REVEAL_DISTANCE = 12;
const REVEAL_DURATION = 0.32;
const STAGGER_STEP = 0.06;

export function Reveal({
  children,
  delay = 0,
  className,
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
}) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      className={className}
      initial={reduceMotion ? false : { opacity: 0, y: REVEAL_DISTANCE }}
      animate={{ opacity: 1, y: 0 }}
      transition={
        reduceMotion ? { duration: 0 } : { duration: REVEAL_DURATION, delay, ease: EASE }
      }
    >
      {children}
    </motion.div>
  );
}

const groupVariants: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: STAGGER_STEP } },
};

export function StaggerGroup({
  children,
  className,
  as = "div",
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "ul";
}) {
  const reduceMotion = useReducedMotion();
  const Container = as === "ul" ? motion.ul : motion.div;

  return (
    <Container
      className={className}
      initial="hidden"
      animate="visible"
      variants={
        reduceMotion ? { hidden: {}, visible: { transition: { staggerChildren: 0 } } } : groupVariants
      }
    >
      {children}
    </Container>
  );
}

export function StaggerItem({
  children,
  className,
  as = "div",
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "li";
}) {
  const reduceMotion = useReducedMotion();
  const Item = as === "li" ? motion.li : motion.div;
  const itemVariants: Variants = reduceMotion
    ? { hidden: { opacity: 1, y: 0 }, visible: { opacity: 1, y: 0, transition: { duration: 0 } } }
    : {
        hidden: { opacity: 0, y: REVEAL_DISTANCE },
        visible: { opacity: 1, y: 0, transition: { duration: REVEAL_DURATION, ease: EASE } },
      };

  return (
    <Item className={className} variants={itemVariants}>
      {children}
    </Item>
  );
}
