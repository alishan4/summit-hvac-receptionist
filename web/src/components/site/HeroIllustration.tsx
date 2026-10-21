/** Original vector artwork: a Colorado home under the peaks, warm inside, snow outside. No third-party imagery. */
export function HeroIllustration({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 560 460" role="img" aria-label="Illustration of a cozy home beneath snowy mountains" className={className}>
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#ffe6d2" /><stop offset="1" stopColor="#fff8f1" />
        </linearGradient>
        <linearGradient id="peakA" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#5b6b86" /><stop offset="1" stopColor="#3d4a63" />
        </linearGradient>
        <linearGradient id="peakB" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#7d8ca6" /><stop offset="1" stopColor="#566580" />
        </linearGradient>
        <radialGradient id="glow" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor="#ffd27a" /><stop offset="1" stopColor="#f59e0b" />
        </radialGradient>
      </defs>
      <rect width="560" height="460" rx="36" fill="url(#sky)" />
      <circle cx="430" cy="92" r="46" fill="#ffd9a8" opacity="0.8" />
      <circle cx="430" cy="92" r="30" fill="#ffc27a" />
      {/* far + near peaks with snow caps */}
      <path d="M-10 330 130 150 215 250 300 130 410 270 470 200 570 330Z" fill="url(#peakB)" />
      <path d="M130 150 100 190 130 178 150 196 170 178 185 200 130 150Z" fill="#fff" opacity="0.9" />
      <path d="M300 130 262 184 292 172 312 192 336 170 352 190 300 130Z" fill="#fff" opacity="0.9" />
      <path d="M-10 350 90 230 170 320 270 210 380 340 470 260 570 350 570 460 -10 460Z" fill="url(#peakA)" />
      <path d="M270 210 238 252 262 244 280 258 300 242 318 256 270 210Z" fill="#fff" opacity="0.95" />
      <path d="M-10 372C120 340 260 362 380 350 470 342 520 352 570 348V460H-10Z" fill="#f3f6fb" />
      {/* house */}
      <g transform="translate(150 232)">
        <ellipse cx="130" cy="178" rx="150" ry="14" fill="#2b3550" opacity="0.14" />
        <rect x="24" y="68" width="212" height="108" rx="6" fill="#fffdf9" stroke="#e7d9c9" strokeWidth="2" />
        <path d="M6 76 130 6 254 76Z" fill="#b8420c" />
        <path d="M6 76 130 6 254 76" fill="none" stroke="#8f3207" strokeWidth="4" strokeLinejoin="round" />
        <path d="M30 70 130 14 230 70 214 70 130 24 46 70Z" fill="#fff" opacity="0.85" />
        <rect x="196" y="22" width="22" height="42" fill="#8a97ad" />
        <rect x="192" y="16" width="30" height="9" rx="2" fill="#6b7993" />
        <rect x="52" y="96" width="62" height="50" rx="5" fill="url(#glow)" />
        <path d="M83 96v50M52 121h62" stroke="#fff4dc" strokeWidth="3" />
        <rect x="146" y="96" width="62" height="50" rx="5" fill="url(#glow)" />
        <path d="M177 96v50M146 121h62" stroke="#fff4dc" strokeWidth="3" />
        <rect x="108" y="120" width="44" height="56" rx="6" fill="#254a7d" />
        <circle cx="142" cy="150" r="3" fill="#ffd27a" />
      </g>
      {/* thermostat card */}
      <g transform="translate(36 40)">
        <rect width="142" height="78" rx="18" fill="#fff" stroke="#eadfd2" />
        <text x="18" y="30" fontFamily="system-ui, sans-serif" fontSize="12" fill="#7a6a5b" fontWeight="600">INSIDE</text>
        <text x="18" y="62" fontFamily="system-ui, sans-serif" fontSize="30" fill="#1f2a44" fontWeight="700">72°F</text>
        <circle cx="112" cy="40" r="15" fill="#fde8d8" />
        <path d="M112 29c3 5 7 7 7 12a7 7 0 1 1-14 0c0-5 4-7 7-12Z" fill="#d9480f" />
      </g>
      {/* booked chip */}
      <g transform="translate(330 346)">
        <rect width="196" height="64" rx="16" fill="#fff" stroke="#e5ece8" />
        <circle cx="32" cy="32" r="14" fill="#16a34a" />
        <path d="m25 32 5 5 9-10" fill="none" stroke="#fff" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />
        <text x="56" y="28" fontFamily="system-ui, sans-serif" fontSize="12" fill="#14532d" fontWeight="700">Visit booked</text>
        <text x="56" y="46" fontFamily="system-ui, sans-serif" fontSize="12" fill="#5b6b66">Tomorrow, 8–10 AM</text>
      </g>
      {/* snowflakes */}
      {[[60, 190, 6], [96, 150, 4], [470, 150, 5], [510, 220, 4], [40, 270, 4], [500, 300, 6]].map(([x, y, r], i) => (
        <g key={i} stroke="#fff" strokeWidth="2" strokeLinecap="round" opacity="0.95">
          <path d={`M${x - r} ${y}h${r * 2}M${x} ${y - r}v${r * 2}M${x - r * 0.7} ${y - r * 0.7}l${r * 1.4} ${r * 1.4}M${x + r * 0.7} ${y - r * 0.7}l${-r * 1.4} ${r * 1.4}`} />
        </g>
      ))}
    </svg>
  );
}
