// Animated brand logo — the "Delegate" wordmark with the signature
// pulsing blue spark. Pure inline SVG + CSS so it autoplays on every
// browser (including iOS Safari) with no play-button overlay.
export default function AnimatedLogo() {
  return (
    <svg className="brand-logo-svg" viewBox="0 0 600 140" xmlns="http://www.w3.org/2000/svg"
         role="img" aria-label="Delegate">
      <defs>
        <radialGradient id="dl-spark" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#eaf8ff" />
          <stop offset="45%" stopColor="#4fc3f7" />
          <stop offset="100%" stopColor="#2b9fe0" />
        </radialGradient>
        <style>{`
          @keyframes dl-pulse { 0%,100% { transform: scale(1); opacity: 1; }
                                50% { transform: scale(1.18); opacity: .9; } }
          @keyframes dl-halo  { 0%,100% { transform: scale(.7); opacity: .55; }
                                50% { transform: scale(1.5); opacity: 0; } }
          .dl-spark { transform-box: fill-box; transform-origin: center;
                      animation: dl-pulse 2s ease-in-out infinite; }
          .dl-halo  { transform-box: fill-box; transform-origin: center;
                      animation: dl-halo 2s ease-in-out infinite; }
        `}</style>
      </defs>

      {/* wordmark */}
      <text x="4" y="100" fontFamily="Syne, Inter, Arial, sans-serif"
            fontWeight="800" fontSize="98" letterSpacing="-4" fill="#1E2A39">Delegate</text>

      {/* connector line from the word up to the spark */}
      <line x1="500" y1="64" x2="544" y2="24" stroke="#1E2A39" strokeWidth="6"
            strokeLinecap="round" />

      {/* glowing spark */}
      <circle className="dl-halo" cx="548" cy="20" r="14" fill="#4fc3f7" />
      <circle className="dl-spark" cx="548" cy="20" r="9" fill="url(#dl-spark)" />
    </svg>
  );
}
