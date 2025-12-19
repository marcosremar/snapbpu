/**
 * Modal Component - Adaptado do TailAdmin para Dumont Cloud
 * Paleta: Dark theme com accent verde (#4ade80, #22c55e)
 */

import { useRef, useEffect } from "react";
import { X } from 'lucide-react';

export const Modal = ({
  isOpen,
  onClose,
  className = "",
  children,
  showCloseButton = true,
  isFullscreen = false,
  size = "md", // sm, md, lg, xl, full
  title,
}) => {
  const modalRef = useRef(null);

  // Handle Escape key
  useEffect(() => {
    const handleEscape = (event) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
    }

    return () => {
      document.removeEventListener("keydown", handleEscape);
    };
  }, [isOpen, onClose]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "unset";
    }

    return () => {
      document.body.style.overflow = "unset";
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const sizeClasses = {
    sm: "max-w-sm",
    md: "max-w-md",
    lg: "max-w-lg",
    xl: "max-w-xl",
    "2xl": "max-w-2xl",
    full: "max-w-full mx-4",
  };

  const contentClasses = isFullscreen
    ? "w-full h-full"
    : `relative w-full ${sizeClasses[size]} rounded-2xl bg-[#131713] border border-gray-800/50 shadow-2xl`;

  return (
    <div className="fixed inset-0 flex items-center justify-center overflow-y-auto z-[99999]">
      {/* Backdrop */}
      {!isFullscreen && (
        <div
          className="fixed inset-0 h-full w-full bg-black/60 backdrop-blur-sm"
          onClick={onClose}
        />
      )}

      {/* Modal Content */}
      <div
        ref={modalRef}
        className={`${contentClasses} ${className} animate-modal-in`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header with close button */}
        {(title || showCloseButton) && (
          <div className="flex items-center justify-between p-4 border-b border-gray-800/50">
            {title && (
              <h3 className="text-lg font-semibold text-white">{title}</h3>
            )}
            {showCloseButton && (
              <button
                onClick={onClose}
                className="flex h-9 w-9 items-center justify-center rounded-full bg-[#1a1f1a] text-gray-400 transition-colors hover:bg-[#2a352a] hover:text-white"
              >
                <X size={20} />
              </button>
            )}
          </div>
        )}

        {/* Body */}
        <div className={title || showCloseButton ? "" : ""}>{children}</div>
      </div>
    </div>
  );
};

// Modal Header (para uso separado)
export const ModalHeader = ({ children, className = "" }) => (
  <div className={`p-4 border-b border-gray-800/50 ${className}`}>
    {children}
  </div>
);

// Modal Body
export const ModalBody = ({ children, className = "" }) => (
  <div className={`p-4 ${className}`}>{children}</div>
);

// Modal Footer
export const ModalFooter = ({ children, className = "" }) => (
  <div className={`p-4 border-t border-gray-800/50 flex justify-end gap-3 ${className}`}>
    {children}
  </div>
);

// Confirmation Modal
export const ConfirmModal = ({
  isOpen,
  onClose,
  onConfirm,
  title = "Confirmar",
  message,
  confirmText = "Confirmar",
  cancelText = "Cancelar",
  variant = "danger", // danger, warning, info
}) => {
  const variantStyles = {
    danger: "bg-red-500 hover:bg-red-600",
    warning: "bg-yellow-500 hover:bg-yellow-600 text-black",
    info: "bg-green-500 hover:bg-green-600",
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="sm" title={title}>
      <ModalBody>
        <p className="text-gray-400">{message}</p>
      </ModalBody>
      <ModalFooter>
        <button
          onClick={onClose}
          className="px-4 py-2 text-sm font-medium text-gray-400 bg-[#1a1f1a] rounded-lg hover:bg-[#2a352a] transition-colors"
        >
          {cancelText}
        </button>
        <button
          onClick={() => {
            onConfirm();
            onClose();
          }}
          className={`px-4 py-2 text-sm font-medium text-white rounded-lg transition-colors ${variantStyles[variant]}`}
        >
          {confirmText}
        </button>
      </ModalFooter>
    </Modal>
  );
};

export default Modal;
