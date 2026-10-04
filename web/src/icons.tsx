type P = { size?: number };
const svg = (size: number, path: React.ReactNode, stroke = 2) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke}
    strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{path}</svg>
);

export const Close = ({ size = 24 }: P) => svg(size, <path d="M5 5l14 14M19 5L5 19" />, 1.6);
export const ChevronLeft = ({ size = 32 }: P) => svg(size, <path d="M15 4l-8 8 8 8" />, 1.4);
export const ChevronRight = ({ size = 32 }: P) => svg(size, <path d="M9 4l8 8-8 8" />, 1.4);
export const Check = ({ size = 16 }: P) => svg(size, <path d="M4 12.5l5 5L20 6.5" />, 2.2);
export const Ban = ({ size = 16 }: P) => svg(size, <><circle cx="12" cy="12" r="8.5" /><path d="M6 18L18 6" /></>, 1.8);
export const Cards = ({ size = 26 }: P) =>
  svg(size, <><rect x="7" y="4" width="12" height="16" rx="2" /><path d="M5 7.5v10.5a2 2 0 002 2h9" /></>, 1.5);
export const Sparkle = ({ size = 16 }: P) =>
  svg(size, <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z" />, 1.6);
export const External = ({ size = 13 }: P) => svg(size, <path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 01-1 1H5a1 1 0 01-1-1V7a1 1 0 011-1h5" />, 1.8);
