import * as React from "react"
import * as AvatarPrimitive from "@radix-ui/react-avatar"

const Avatar = React.forwardRef(({ className, ...props }, ref) => (
  <AvatarPrimitive.Root
    ref={ref}
    className={`relative inline-flex h-10 w-10 select-none items-center justify-center rounded-full bg-gradient-to-br from-green-500/30 to-green-600/30 border border-green-500/30 ${className || ""}`}
    {...props}
  />
))
Avatar.displayName = AvatarPrimitive.Root.displayName

const AvatarImage = React.forwardRef(({ className, ...props }, ref) => (
  <AvatarPrimitive.Image
    ref={ref}
    className={`h-full w-full rounded-full object-cover ${className || ""}`}
    {...props}
  />
))
AvatarImage.displayName = AvatarPrimitive.Image.displayName

const AvatarFallback = React.forwardRef(({ className, ...props }, ref) => (
  <AvatarPrimitive.Fallback
    ref={ref}
    className={`flex h-full w-full items-center justify-center rounded-full bg-gradient-to-br from-green-500 to-green-600 text-sm font-medium text-black ${className || ""}`}
    {...props}
  />
))
AvatarFallback.displayName = AvatarPrimitive.Fallback.displayName

export { Avatar, AvatarImage, AvatarFallback }
