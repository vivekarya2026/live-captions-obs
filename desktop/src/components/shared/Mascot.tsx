import React from "react";
import { AppMark } from "../icons/AppTextLogo";

interface MascotProps {
  /** Height in px. */
  size: number;
  /** Wave once on arrival, or a little bounce (re-key it to play again). */
  animation?: "wave" | "slap" | null;
}

/** The Live Captions mark, optionally animated (onboarding screens). */
export const Mascot: React.FC<MascotProps> = ({ size, animation = null }) => (
  <span
    style={{ width: size, height: size }}
    className={`relative block origin-[30%_90%] select-none ${animation === "wave" ? "animate-wave" : animation === "slap" ? "animate-slap" : ""}`}
  >
    <AppMark size={size} />
  </span>
);
