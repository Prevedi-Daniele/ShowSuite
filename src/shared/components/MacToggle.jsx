import React from 'react';

/**
 * MacToggle - Interruttore Switch stile Apple iOS / macOS
 */
export default function MacToggle({
  checked = false,
  onChange,
  disabled = false,
  label,
  description,
  className = '',
}) {
  return (
    <label className={`inline-flex items-center cursor-pointer select-none ${disabled ? 'opacity-40 cursor-not-allowed' : ''} ${className}`}>
      <div className="relative">
        <input
          type="checkbox"
          className="sr-only"
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange && onChange(e.target.checked)}
        />
        <div
          className={`w-9 h-5 rounded-full transition-colors duration-200 border ${
            checked
              ? 'bg-[#30d158] border-[#2bbd4f]'
              : 'bg-[#3a3a3c] border-[#48484a]'
          }`}
        ></div>
        <div
          className={`absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full shadow-md transition-transform duration-200 ${
            checked ? 'transform translate-x-4' : ''
          }`}
        ></div>
      </div>
      {(label || description) && (
        <div className="ml-2.5">
          {label && <div className="text-xs font-medium text-mac-text">{label}</div>}
          {description && <div className="text-[11px] text-mac-muted">{description}</div>}
        </div>
      )}
    </label>
  );
}
