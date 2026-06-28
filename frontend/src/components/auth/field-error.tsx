/** Mensaje de error a nivel de campo. */
export function FieldError({ message }: { message?: string }) {
  if (!message) return null
  return <p className="text-destructive text-sm">{message}</p>
}

/** Aviso de error a nivel de formulario. */
export function FormError({ message }: { message?: string }) {
  if (!message) return null
  return (
    <div
      role="alert"
      className="border-destructive/30 bg-destructive/10 text-destructive rounded-lg border px-3 py-2 text-sm"
    >
      {message}
    </div>
  )
}
