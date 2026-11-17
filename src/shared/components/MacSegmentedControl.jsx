import React from 'react';

/**
 * MacSegmentedControl - Segmented control fedele allo standard Apple macOS
 * Angoli concentricamente arrotondati, contrasto semantico e sliding capsule background
 */
export default function MacSegmentedControl({
  options = [],
  value,
  onChange,
  size = 'md',
  className = '',
}) {
  const sizeStyles = {
    sm: 'p-[2px] text-[11px] h-[24px]',
    md: 'p-[2px] text-xs h-[28px]',
    lg: 'p-[3px] text-sm h-[32px]',
  };

  const itemPaddings = {
    sm: 'px-2.5 py-0.5 min-h-[20px]',
    md: 'px-3 py-1 min-h-[24px]',
    lg: 'px-4 py-1.5 min-h-[26px]',
  };

  return (
    <div
      className={`inline-flex items-center rounded-[6px] bg-[#161619]/90 border border-white/[0.08] shadow-inner select-none ${sizeStyles[size]} ${className}`}
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
            className={`relative flex items-center justify-center space-x-1.5 font-medium rounded-[5px] transition-all duration-150 ${itemPaddings[size]} ${
              isSelected
                ? 'bg-[#323238] text-white shadow-[0_1px_2px_rgba(0,0,0,0.5)] border border-white/[0.12] font-semibold'
                : 'text-[#8e8e93] hover:text-[#f5f5f7] hover:bg-white/[0.04]'
            }`}
          >
            {Icon && <Icon size={size === 'sm' ? 12 : 13} className={isSelected ? 'text-[#0a84ff]' : 'opacity-65'} />}
            <span className="leading-none">{option.label}</span>
          </button>
        );
      })}
    </div>
  );
}
