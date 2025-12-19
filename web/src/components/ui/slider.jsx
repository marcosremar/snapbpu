import * as React from "react"
import * as SliderPrimitive from "@radix-ui/react-slider"
import { cn } from "../../lib/utils"

const Slider = React.forwardRef(({ className, ...props }, ref) => (
  <SliderPrimitive.Root
    ref={ref}
    className={cn(
      "relative flex w-full touch-none select-none items-center",
      className
    )}
    {...props}
  >
    <SliderPrimitive.Track className="relative h-3 w-full grow overflow-hidden rounded-full bg-gradient-to-r from-gray-700/30 to-gray-600/30">
      <SliderPrimitive.Range className="absolute h-full bg-gradient-to-r from-emerald-500 to-emerald-600 shadow-lg shadow-emerald-500/30" />
    </SliderPrimitive.Track>
    <SliderPrimitive.Thumb className="block h-5 w-5 rounded-full border-2 border-emerald-400 bg-white shadow-xl shadow-emerald-500/40 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0e110e] disabled:pointer-events-none disabled:opacity-50 hover:shadow-2xl hover:shadow-emerald-500/50 hover:scale-125" />
  </SliderPrimitive.Root>
))
Slider.displayName = SliderPrimitive.Root.displayName

export { Slider }
