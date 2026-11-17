import React, { useEffect } from 'react';
import { X } from 'lucide-react';

/**
 * MacModal - Finestra di dialogo modale stile macOS
 */
export default function MacModal({
  isOpen,
  onClose,
  title,
  children,
  width = 'max-w-2xl',
  footer,
}) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div
        className={`w-full ${width} bg-[#1e1e22] border border-[#3e3e46] rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh] animate-scale-up`}
      >
        {/* Header con titolo stile macOS */}
        <div className="h-10 bg-[#25252b] border-b border-[#35353d] flex items-center justify-between px-4 select-none">
          <span className="text-xs font-semibold text-zinc-200 tracking-wide">{title}</span>
          <button
            onClick={onClose}
            className="w-5 h-5 rounded flex items-center justify-center text-zinc-400 hover:text-white hover:bg-white/10 transition"
          >
            <X size={14} />
          </button>
        </div>

        {/* Contenuto scorrevole */}
        <div className="p-5 overflow-y-auto flex-1 text-xs text-zinc-300">
          {children}
        </div>

        {/* Footer opzionale */}
        {footer && (
          <div className="h-12 bg-[#25252b] border-t border-[#35353d] px-4 flex items-center justify-end space-x-2 select-none">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
