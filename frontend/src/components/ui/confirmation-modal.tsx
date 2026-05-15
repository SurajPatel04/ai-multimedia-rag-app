import React from "react";
import { motion, AnimatePresence } from "motion/react";
import { IconX, IconAlertTriangle } from "@tabler/icons-react";

interface ConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  isDanger?: boolean;
}

export const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = "Confirm",
  cancelText = "Cancel",
  isDanger = false,
}) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/60"
          />

          {/* Modal content */}
          <motion.div
            initial={{ opacity: 0, scale: 0.98, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.98, y: 8 }}
            transition={{
              type: "spring",
              damping: 30,
              stiffness: 400,
            }}
            className="relative w-full max-w-sm overflow-hidden rounded-2xl border border-neutral-800 bg-neutral-900 p-6 shadow-2xl"
          >
            <div className="flex items-start justify-between">
              <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${isDanger ? "bg-red-500/10 text-red-500" : "bg-blue-500/10 text-blue-500"}`}>
                <IconAlertTriangle className="h-5 w-5" />
              </div>
              <button
                onClick={onClose}
                className="rounded-lg p-1 text-neutral-500 transition hover:bg-neutral-800 hover:text-neutral-300"
              >
                <IconX className="h-5 w-5" />
              </button>
            </div>

            <div className="mt-4">
              <h3 className="text-lg font-semibold text-white tracking-tight">{title}</h3>
              <p className="mt-2 text-sm text-neutral-400 leading-relaxed">
                {message}
              </p>
            </div>

            <div className="mt-8 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                type="button"
                onClick={onClose}
                className="flex-1 rounded-xl border border-neutral-800 px-4 py-2.5 text-sm font-medium text-neutral-400 transition hover:bg-neutral-800 hover:text-white sm:flex-none sm:min-w-[80px]"
              >
                {cancelText}
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                type="button"
                onClick={() => {
                  onConfirm();
                  onClose();
                }}
                className={`flex-1 rounded-xl px-4 py-2.5 text-sm font-medium text-white transition shadow-lg sm:flex-none sm:min-w-[80px] ${
                  isDanger
                    ? "bg-red-600 hover:bg-red-500 shadow-red-900/20"
                    : "bg-blue-600 hover:bg-blue-500 shadow-blue-900/20"
                }`}
              >
                {confirmText}
              </motion.button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
