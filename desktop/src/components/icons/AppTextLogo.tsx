import React from "react";

/** The Live Captions mark: a speech bubble with two caption lines. */
export const AppMark: React.FC<{
  size?: number;
  className?: string;
  width?: number | string;
  height?: number | string;
}> = ({ size = 24, className = "", width, height }) => (
  <svg
    width={width ?? size}
    height={height ?? size}
    viewBox="0 0 32 32"
    fill="none"
    className={className}
    aria-hidden
  >
    <path
      d="M6 5h20a3 3 0 0 1 3 3v12a3 3 0 0 1-3 3H14l-6 5v-5H6a3 3 0 0 1-3-3V8a3 3 0 0 1 3-3Z"
      fill="var(--color-logo-primary)"
      stroke="var(--color-mascot-line)"
      strokeWidth="2"
      strokeLinejoin="round"
    />
    <path
      d="M9 12h14M9 16.5h9"
      stroke="var(--color-mascot-line)"
      strokeWidth="2.2"
      strokeLinecap="round"
    />
  </svg>
);

/** Mark + "Live Captions" wordmark (sidebar, onboarding). */
// Product name: brand text, not translated.
const NAME_TOP = "Live";
const NAME_BOTTOM = "Captions";

export const AppTextLogo: React.FC<{ className?: string; mark?: boolean }> = ({
  className = "",
  mark = true,
}) => (
  <div className={`flex items-center gap-2 select-none ${className}`}>
    {mark && <AppMark size={28} />}
    <span className="font-display font-bold text-[17px] leading-[1.05] tracking-tight">
      {NAME_TOP}
      <br />
      {NAME_BOTTOM}
    </span>
  </div>
);

export default AppTextLogo;
