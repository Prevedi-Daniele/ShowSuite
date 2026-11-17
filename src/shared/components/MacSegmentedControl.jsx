import React from 'react';

/**
 * MacSegmentedControl - Segmented control in stile Apple macOS
 * @param {Array} options - [{ id, label, icon: Icon, badge }]
 * @param {string} value - ID dell'opzione attiva
 * @param {function} onChange - Callback (newId) => void
 */
export default function MacSegmentedControl({
  options = [],
  value,
  onChange,
  size = 'md',
  className = '',
}) {
  const sizeStyles = {
    sm: 'p-0.5 text-[11px]',
    md: 'p-1 text-xs',
    lg: 'p-1.5 text-sm',
  };

  const itemPaddings = {
    sm: 'px-2 py-0.5 min-h-[22px]',
    md: 'px-3 py-1 min-h-[26px]',
    lg: 'px-4 py-1.5 min-h-[30px]',
  };

  return (
    <div
      className={`inline-flex items-center rounded-lg bg-[#141416]/90 border border-[#2e2e33] shadow-inner select-none ${sizeStyles[size]} ${className}`}
      role="tablist"
    >
      {options.map((option) => {
        const isSelected = option.id === value;
        const Icon = option.icon;

        return (
          <button
            key={option.id}
            type="button"
            role="tab"
            aria-selected={isSelected}
            onClick={() => onChange && onChange(option.id)}
            className={`flex items-center justify-center space-x-1.5 font-medium rounded-md transition-all duration-150 ${itemPaddings[size]} ${
              isSelected
                ? 'bg-gradient-to-b from-[#3c3c43] to-[#2e2e34] text-white shadow-sm border border-[#505058]/60 font-semibold'
                : 'text-mac-muted hover:text-mac-text hover:bg-white/[0.04]'
            }`}
          >
            {Icon && <Icon size={size === 'sm' ? 12 : 14} className={isSelected ? 'text-mac-accent' : 'opacity-70'} />}
            <span>{option.label}</span>
            {option.badge !== undefined && (
              <span className={`ml-1 text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                isSelected ? 'bg-mac-accent text-white' : 'bg-zinc-800 text-zinc-400'
              }`}>
                {option.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
