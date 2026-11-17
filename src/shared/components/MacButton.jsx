import React from 'react';

/**
 * MacButton - Bottone conforme all'Apple Human Interface Guidelines (macOS Dark)
 * Supporta varianti native per controlli operativi di QLab 5 & Lightkey
 */
export default function MacButton({
  children,
  variant = 'default',
  size = 'md',
  onClick,
  disabled = false,
  className = '',
  icon: Icon,
  title = '',
  active = false,
}) {
  const sizeClasses = {
    xs: 'px-2 py-0.5 text-[10px] rounded h-5 min-w-[20px] gap-1',
    sm: 'px-2.5 py-1 text-[11px] rounded-[5px] h-[26px] min-w-[26px] gap-1.5',
    md: 'px-3 py-1.5 text-xs rounded-md h-7 min-w-[30px] gap-1.5',
    lg: 'px-4 py-2 text-sm rounded-lg h-9 min-w-[36px] gap-2',
    huge: 'px-6 py-3 text-2xl font-black rounded-xl h-20 min-w-[124px] gap-3', // QLab Giant GO
  };

  const variantClasses = {
    // macOS Standard Button
    default: `bg-[#2a2a30] hover:bg-[#34343c] active:bg-[#222227] text-[#f5f5f7] 
      border border-white/10 shadow-mac-btn`,
    
    // Prominent Blue Action Button (Done, Save, Primary)
    primary: `bg-[#0071e3] hover:bg-[#0077ed] active:bg-[#005bb5] text-white 
      border border-blue-400/30 shadow-[0_1px_3px_rgba(0,113,227,0.4)] font-medium`,
    
    // QLab 5 Giant GO Button (Vibrant Apple Green Glow)
    'qlab-go': `bg-gradient-to-b from-[#30d158] via-[#28cd41] to-[#22b339] 
      hover:from-[#34c759] hover:to-[#28cd41] active:from-[#1ea833] active:to-[#1a8c2b]
      text-[#051f0b] font-black tracking-wider border border-[#5ee67f]/60 shadow-qlab-go`,
    
    // QLab 5 Panic Button (Emergency Red)
    panic: `bg-gradient-to-b from-[#ff453a] to-[#d70015] hover:from-[#ff5b52] hover:to-[#e00018]
      active:from-[#b30012] active:to-[#8f000e] text-white font-bold border border-[#ff8580]/50 shadow-qlab-panic`,
    
    // Destructive / Stop Button
    destructive: `bg-[#2a1717] hover:bg-[#3d1a1a] active:bg-[#1f1010] text-[#ff453a] 
      border border-red-500/25`,

    // Flat Toolbar Items (QLab Dock & Window Controls)
    toolbar: `bg-transparent hover:bg-white/[0.08] active:bg-white/[0.14] text-[#a1a1a6] hover:text-[#f5f5f7] border border-transparent 
      ${active ? 'bg-white/[0.12] text-white !border-white/15 shadow-inner' : ''}`,

    // Segmented / Subtle Control
    subtle: `bg-white/[0.04] hover:bg-white/[0.08] active:bg-white/[0.12] text-[#d1d1d6] border border-white/[0.06]`,
  };

  return (
    <button
      type="button"
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      title={title}
      className={`inline-flex items-center justify-center font-medium transition-all duration-100 select-none 
        focus:outline-none focus-visible:ring-2 focus-visible:ring-mac-accent active:scale-[0.98]
        ${disabled ? 'opacity-35 cursor-not-allowed pointer-events-none' : 'cursor-pointer'}
        ${sizeClasses[size] || sizeClasses.md}
        ${variantClasses[variant] || variantClasses.default}
        ${className}`}
    >
      {Icon && <Icon size={size === 'huge' ? 26 : size === 'sm' || size === 'xs' ? 13 : 15} className="shrink-0" />}
      {children && <span className="truncate">{children}</span>}
    </button>
  );
}
