import type { ReactNode } from "react";

/**
 * Modal shell only. The error banner and the Cancel/Save buttons live inside each
 * resource's own form, because they are wired to that form's RHF instance.
 */
export function FormDialog({
  open,
  title,
  children,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/30">
      <div className="w-96 rounded border border-gray-200 bg-white p-4 shadow-lg">
        <h2 className="mb-2 text-lg font-semibold">{title}</h2>
        {children}
      </div>
    </div>
  );
}
