import React from "react";

/** The Live Captions mark: a sound wave turning into caption lines, on a
 *  Royal Blue tile (same drawing as the app icon, design/icon/app.svg). */
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
    <rect width="32" height="32" rx="7.5" fill="var(--color-background-ui)" />
    <g stroke="#fff" strokeWidth="2.6" strokeLinecap="round">
      <path d="M6 14v4M10 10.5v11M14 12.5v7" />
      <path d="M18.5 12h7.5M18.5 16h6.3M18.5 20h3.8" />
    </g>
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
