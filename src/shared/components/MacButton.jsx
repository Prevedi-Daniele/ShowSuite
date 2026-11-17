import React from 'react';

/**
 * MacButton - Bottone in stile nativo macOS Dark
 * Varianti: 'default' (grigio neutro), 'primary' (blu Apple), 'qlab-go' (verde fluo), 'panic' (rosso scuro), 'toolbar' (flat per barre strumenti)
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
    sm: 'px-2 py-0.5 text-xs rounded-md h-6 min-w-[24px]',
    md: 'px-3 py-1 text-xs rounded-md h-7 min-w-[28px]',
    lg: 'px-4 py-2 text-sm rounded-lg h-9 min-w-[36px]',
    huge: 'px-8 py-4 text-2xl font-bold rounded-xl h-20 min-w-[120px]', // per il tasto GO di QLab
  };

  const variantClasses = {
    default: `bg-gradient-to-b from-[#3a3a40] to-[#2e2e34] hover:from-[#45454c] hover:to-[#38383f] 
      text-[#f4f4f5] border border-[#484850]/70 active:from-[#25252a] active:to-[#222226] shadow-sm`,
    primary: `bg-gradient-to-b from-[#0a84ff] to-[#0071e3] hover:from-[#2292ff] hover:to-[#0a84ff] 
      text-white border border-[#3ca2ff]/40 active:from-[#0062c4] active:to-[#0052a3] shadow-sm shadow-blue-900/30`,
    'qlab-go': `bg-gradient-to-b from-[#30d158] to-[#248a3d] hover:from-[#3ce066] hover:to-[#2cb04b] 
      text-black font-black tracking-wider border border-[#52e878]/50 active:from-[#1b6b2f] active:to-[#175c28] shadow-lg shadow-green-950/50`,
    panic: `bg-gradient-to-b from-[#ff453a] to-[#d70015] hover:from-[#ff6961] hover:to-[#e00018] 
      text-white font-bold border border-[#ff8580]/50 active:from-[#b30012] active:to-[#8f000e] shadow-lg shadow-red-950/50`,
    toolbar: `bg-transparent hover:bg-white/10 text-mac-muted hover:text-white border border-transparent 
      ${active ? 'bg-white/15 text-white border-mac-border/60 shadow-inner' : ''}`,
    destructive: `bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30`,
  };

  return (
    <button
      type="button"
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      title={title}
      className={`inline-flex items-center justify-center font-medium transition-all duration-75 select-none 
        focus:outline-none focus:ring-1 focus:ring-mac-accent/70 active:scale-[0.98]
        ${disabled ? 'opacity-40 cursor-not-allowed filter grayscale' : 'cursor-pointer'}
        ${sizeClasses[size] || sizeClasses.md}
        ${variantClasses[variant] || variantClasses.default}
        ${className}
      `}
    >
      {Icon && <Icon size={size === 'huge' ? 28 : size === 'sm' ? 12 : 14} className={children ? 'mr-1.5' : ''} />}
      {children}
    </button>
  );
}
