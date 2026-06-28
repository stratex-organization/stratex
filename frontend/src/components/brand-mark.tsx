import { cn } from "@/lib/utils"

type BrandMarkProps = {
  /** Tamaño del badge cuadrado con la "S". */
  size?: number
  /** Clase para el texto "Stratex" (permite ajustar color sobre fondos oscuros). */
  titleClassName?: string
  subtitleClassName?: string
  className?: string
}

/** Logotipo de Stratex: badge naranja con "S" + "Stratex" / "by Xignux". */
export function BrandMark({
  size = 38,
  titleClassName,
  subtitleClassName,
  className,
}: BrandMarkProps) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div
        className="flex items-center justify-center rounded-[11px] font-extrabold text-white"
        style={{
          width: size,
          height: size,
          fontSize: size * 0.5,
          background: "linear-gradient(145deg,#FF4500,#B81A06)",
        }}
      >
        S
      </div>
      <div className="leading-[1.05]">
        <div className={cn("text-lg font-extrabold tracking-tight", titleClassName)}>Stratex</div>
        <div
          className={cn("mt-0.5 text-[11px] font-medium tracking-wide", subtitleClassName)}
          style={{ color: "var(--sidebar-sub)" }}
        >
          by Xignux
        </div>
      </div>
    </div>
  )
}
