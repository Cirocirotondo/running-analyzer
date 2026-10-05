/** Where to put the phone (Recording Guide): side view and top view. Drawn, not photographed, so it
 *  stays readable at phone width. */
export default function RecordingSetup() {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <svg className="w-full text-[11px]" fill="#404040" viewBox="0 0 300 190" role="img" aria-label="Side view">
        <text x="4" y="12" className="font-semibold" fill="#171717">From the side</text>
        <line x1="0" y1="160" x2="300" y2="160" stroke="#a3a3a3" strokeWidth="1.5"/>
        {/* treadmill */}
        <rect x="190" y="140" width="104" height="14" rx="5" fill="#404040"/>
        <line x1="200" y1="154" x2="200" y2="160" stroke="#404040" strokeWidth="3"/>
        <line x1="284" y1="154" x2="284" y2="160" stroke="#404040" strokeWidth="3"/>
        <path d="M272 140 Q 282 95 266 70" fill="none" stroke="#404040" strokeWidth="4" strokeLinecap="round"/>
        {/* runner */}
        <g stroke="#0078ff" strokeWidth="4" strokeLinecap="round" fill="none">
          <circle cx="236" cy="38" r="7" fill="#0078ff" stroke="none"/>
          <line x1="234" y1="47" x2="230" y2="88"/>
          <path d="M233 56 L222 72 L232 80"/>
          <path d="M233 56 L246 68 L252 58"/>
          <path d="M230 88 L244 112 L234 139"/>
          <path d="M230 88 L216 108 L206 128"/>
        </g>
        {/* good phone on tripod at hip height */}
        <g stroke="#171717" strokeWidth="2" strokeLinecap="round">
          <line x1="34" y1="96" x2="22" y2="160"/><line x1="34" y1="96" x2="46" y2="160"/><line x1="34" y1="96" x2="34" y2="160"/>
        </g>
        <rect x="28" y="78" width="12" height="20" rx="2" fill="#171717"/>
        <line x1="42" y1="88" x2="222" y2="88" stroke="#16a34a" strokeWidth="1.5" strokeDasharray="5 4"/>
        <text x="70" y="82" fill="#15803d">camera at hip height</text>
        {/* distance */}
        <g stroke="#737373" strokeWidth="1"><line x1="34" y1="174" x2="230" y2="174"/><line x1="34" y1="169" x2="34" y2="179"/><line x1="230" y1="169" x2="230" y2="179"/></g>
        <text x="132" y="187" textAnchor="middle">3–4 m</text>
        {/* bad phone on the floor */}
        <rect x="96" y="148" width="18" height="10" rx="2" fill="#d4d4d4"/>
        <g stroke="#dc2626" strokeWidth="2.5" strokeLinecap="round"><line x1="94" y1="142" x2="116" y2="160"/><line x1="116" y1="142" x2="94" y2="160"/></g>
        <text x="105" y="134" textAnchor="middle" fill="#b91c1c">not on the floor</text>
      </svg>
      <svg className="w-full text-[11px]" fill="#404040" viewBox="0 0 300 190" role="img" aria-label="Top view">
        <text x="4" y="12" className="font-semibold" fill="#171717">From above</text>
        {/* treadmill, belt runs left-right */}
        <rect x="70" y="30" width="200" height="60" rx="6" fill="#404040"/>
        <rect x="80" y="38" width="180" height="44" rx="3" fill="#737373"/>
        <rect x="262" y="26" width="10" height="68" rx="3" fill="#262626"/>
        <text x="170" y="64" textAnchor="middle" fill="#fafafa">belt</text>
        {/* runner dot */}
        <circle cx="200" cy="60" r="9" fill="#0078ff"/>
        <path d="M212 60 l8 0 m-4 -4 l4 4 l-4 4" stroke="#fafafa" strokeWidth="2" fill="none"/>
        {/* phone + line of sight */}
        <rect x="190" y="160" width="20" height="10" rx="2" fill="#171717"/>
        <line x1="200" y1="158" x2="200" y2="74" stroke="#16a34a" strokeWidth="1.5" strokeDasharray="5 4"/>
        <path d="M200 100 h10 v-10" fill="none" stroke="#15803d" strokeWidth="1.5"/>
        <text x="212" y="130" fill="#15803d">at a right angle</text>
        <text x="212" y="143" fill="#15803d">to the belt</text>
        {/* bad: neighbouring treadmill */}
        <rect x="20" y="118" width="110" height="34" rx="5" fill="#d4d4d4"/>
        <rect x="62" y="128" width="16" height="9" rx="2" fill="#a3a3a3"/>
        <g stroke="#dc2626" strokeWidth="2.5" strokeLinecap="round"><line x1="58" y1="124" x2="82" y2="142"/><line x1="82" y1="124" x2="58" y2="142"/></g>
        <text x="75" y="168" textAnchor="middle" fill="#b91c1c">not on another</text>
        <text x="75" y="181" textAnchor="middle" fill="#b91c1c">treadmill</text>
      </svg>
    </div>
  );
}
