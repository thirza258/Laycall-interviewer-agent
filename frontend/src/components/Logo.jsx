export default function Logo({
  className = "w-8 h-8",
  showText = false,
  textClassName = "text-white font-bold text-sm tracking-tight",
  subtitle = null,
  subtitleClassName = "text-[11px] text-[#818cf8] font-medium",
  idPrefix = "mmi-logo",
  containerClassName = "",
  ...props
}) {
  return (
    <div className={`inline-flex items-center gap-2.5 ${containerClassName}`}>
      <svg
        className={className}
        viewBox="0 0 512 512"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-label="My Mock Interview Logo"
        role="img"
        {...props}
      >
        <defs>
          <linearGradient id={`${idPrefix}-bg`} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#4F46E5" />
            <stop offset="45%" stopColor="#4338CA" />
            <stop offset="100%" stopColor="#312E81" />
          </linearGradient>
          <radialGradient id={`${idPrefix}-glow`} cx="25%" cy="20%" r="70%">
            <stop offset="0%" stopColor="#818CF8" stopOpacity="0.4" />
            <stop offset="60%" stopColor="#6366F1" stopOpacity="0.1" />
            <stop offset="100%" stopColor="#4338CA" stopOpacity="0" />
          </radialGradient>
          <linearGradient id={`${idPrefix}-bars`} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#6366F1" />
            <stop offset="50%" stopColor="#4F46E5" />
            <stop offset="100%" stopColor="#7C3AED" />
          </linearGradient>
          <linearGradient id={`${idPrefix}-sparkle`} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#38BDF8" />
            <stop offset="100%" stopColor="#818CF8" />
          </linearGradient>
          <filter id={`${idPrefix}-shadow`} x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="10" stdDeviation="16" floodColor="#1E1B4B" floodOpacity="0.38" />
          </filter>
        </defs>

        <rect width="512" height="512" rx="116" fill={`url(#${idPrefix}-bg)`} />
        <rect width="512" height="512" rx="116" fill={`url(#${idPrefix}-glow)`} />
        <rect width="504" height="504" x="4" y="4" rx="112" fill="none" stroke="white" strokeWidth="3" strokeOpacity="0.2" />

        <g filter={`url(#${idPrefix}-shadow)`}>
          <path
            d="M 160 144
               h 176
               a 48 48 0 0 1 48 48
               v 116
               a 48 48 0 0 1 -48 48
               h -112
               l -68 44
               c 10 -18 16 -34 16 -44
               h -12
               a 48 48 0 0 1 -48 -48
               v -116
               a 48 48 0 0 1 48 -48
               z"
            fill="#FFFFFF"
          />
        </g>

        <g fill={`url(#${idPrefix}-bars)`}>
          <rect x="165" y="194" width="22" height="112" rx="11" />
          <rect x="201" y="222" width="22" height="56" rx="11" />
          <rect x="237" y="206" width="22" height="88" rx="11" />
          <rect x="273" y="222" width="22" height="56" rx="11" />
          <rect x="309" y="194" width="22" height="112" rx="11" />
        </g>

        <path
          d="M 398 92
             Q 398 128 434 128
             Q 398 128 398 164
             Q 398 128 362 128
             Q 398 128 398 92 Z"
          fill={`url(#${idPrefix}-sparkle)`}
        />

        <path
          d="M 436 74
             Q 436 88 450 88
             Q 436 88 436 102
             Q 436 88 422 88
             Q 436 88 436 74 Z"
          fill="#38BDF8"
          opacity="0.95"
        />
      </svg>
      {showText && (
        <div className="flex flex-col leading-tight">
          <span className={textClassName}>Mock Interview</span>
          {subtitle && <span className={subtitleClassName}>{subtitle}</span>}
        </div>
      )}
    </div>
  );
}
