import type { SVGProps } from "react";

const paths: Record<string, React.ReactNode> = {
  home: <><path d="m3 10 9-7 9 7v10H3z"/><path d="M9 20v-7h6v7"/></>,
  book: <><path d="M12 5v15M3 4c4-1 6 0 9 2 3-2 5-3 9-2v15c-4-1-6 0-9 2-3-2-5-3-9-2z"/></>,
  sparkles: <><path d="m12 3 2.7 6.3L21 12l-6.3 2.7L12 21l-2.7-6.3L3 12l6.3-2.7zM20 2v4m-2-2h4"/></>,
  arrowRight: <><path d="M4 12h16m-6-6 6 6-6 6"/></>,
  arrowLeft: <><path d="M20 12H4m6-6-6 6 6 6"/></>,
  plus: <path d="M12 5v14M5 12h14"/>,
  upload: <><path d="M12 16V3m-5 5 5-5 5 5M4 15v5h16v-5"/></>,
  check: <path d="m5 12 4 4L19 6"/>,
  close: <path d="m6 6 12 12M6 18 18 6"/>,
  search: <><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></>,
  chat: <><path d="M21 11a8 8 0 0 1-8 8H7l-4 3v-9a9 9 0 1 1 18-2Z"/><path d="M7 9h10M7 13h6"/></>,
  brain: <><path d="M12 4v16M12 5C8 0 4 5 5 9c-4 2-2 7 1 7 0 5 5 6 6 2M12 5c4-5 8 0 7 4 4 2 2 7-1 7 0 5-5 6-6 2"/><path d="m5 9 3 2m11-2-3 2M6 16l3-2m9 2-3-2"/></>,
  cards: <><rect x="5" y="5" width="15" height="16" rx="3"/><path d="M16 2H5a3 3 0 0 0-3 3v12M9 10h7m-7 4h5"/></>,
  quiz: <><rect x="4" y="3" width="16" height="18" rx="3"/><path d="m8 8 1 1 2-2m-3 7 1 1 2-2m3-5h3m-3 6h3"/></>,
  file: <><path d="M14 2H5v20h14V7zM14 2v6h5M8 12h8m-8 4h6"/></>,
  note: <><path d="M20 12v9H3V4h9M9 15l1-5L19 1l4 4-9 9z"/></>,
  chart: <><path d="M4 3v18h17M8 16v-5m5 5V7m5 9V4"/></>,
  clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l4 2"/></>,
  calendar: <><rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7 2v6m10-6v6M3 11h18m-14 4h3m4 0h3"/></>,
  settings: <><path d="m9 3-1 3-3 1-2 4 2 2v4l4 3 3-1 3 1 4-3v-4l2-2-2-4-3-1-1-3z"/><circle cx="12" cy="12" r="3"/></>,
  logout: <><path d="M9 3H3v18h6M8 12h13m-5-5 5 5-5 5"/></>,
  chevronLeft: <path d="m15 5-7 7 7 7"/>,
  chevronRight: <path d="m9 5 7 7-7 7"/>,
  chevronDown: <path d="m5 9 7 7 7-7"/>,
  zoomIn: <><circle cx="10" cy="10" r="7"/><path d="m16 16 5 5M7 10h6m-3-3v6"/></>,
  zoomOut: <><circle cx="10" cy="10" r="7"/><path d="m16 16 5 5M7 10h6"/></>,
  mic: <><rect x="9" y="2" width="6" height="13" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2m-7 9v3m-4 0h8"/></>,
  stop: <rect x="6" y="6" width="12" height="12" rx="2"/>,
  play: <path d="m8 4 12 8-12 8z"/>,
  volume: <><path d="m11 4-5 4H2v8h4l5 4zm4 3a7 7 0 0 1 0 10m3-13a11 11 0 0 1 0 16"/></>,
  refresh: <><path d="M20 8V3l-4 4M4 16v5l4-4M20 8A8 8 0 0 0 5 7m-1 9a8 8 0 0 0 15 1"/></>,
  info: <><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7v.1"/></>,
  heart: <path d="M12 21 3 12C-3 4 7-1 12 6 17-1 27 4 21 12z"/>,
  bell: <><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M9 21h6"/></>,
  grid: <><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></>,
  download: <><path d="M12 3v13m-5-5 5 5 5-5M3 17v4h18v-4"/></>,
};

export function Icon({name,size=20,...props}:{name:string;size?:number}&SVGProps<SVGSVGElement>) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name] || paths.book}</svg>;
}
