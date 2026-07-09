<script setup lang="ts">
/**
 * Animated border beam. Inspired by vscode's chat input.
 * @see https://github.com/microsoft/vscode/blob/1.128.0/src/vs/workbench/contrib/chat/browser/widget/media/chat.css#L900-L1025
 */
import { cn } from "@/lib/utils"

const props = withDefaults(
  defineProps<{
    as?: string
    /** The duration of the border beam animation in seconds. */
    duration?: `${number}s`
    /** The color of the beam. */
    color?: string
    /** Whether to reverse the animation direction. */
    reverse?: boolean
    /** The border width of the beam in pixels. */
    borderWidth?: `${number}px`
    /** The angular size of the bright arc, in degrees (0-360). Larger values produce a longer comet tail. */
    arcRadius?: number
    /** Additional classes. */
    class?: string
  }>(),
  {
    as: "div",
    duration: "4s",
    color: "var(--color-primary)",
    reverse: false,
    borderWidth: "1px",
    arcRadius: 90,
  },
)
</script>

<template>
  <component
    :is="props.as"
    :class="
      cn(
        'animate-border-beam border-primary/20 relative block border-(length:--border-beam-width)',
        props.class,
      )
    "
    :style="{
      '--border-beam-duration': props.duration,
      '--border-beam-width': props.borderWidth,
      '--border-beam-color': props.color,
      '--border-beam-arc-radius': `${props.arcRadius}deg`,
      '--border-beam-spin-angle': props.reverse ? '495deg' : '135deg',
      '--border-beam-direction': props.reverse ? 'reverse' : 'normal',
    }"
  >
    <slot />
  </component>
</template>

<style scoped>
@property --border-beam-spin-angle {
  syntax: "<angle>";
  inherits: false;
  initial-value: 135deg;
}

@keyframes border-spin {
  from {
    --border-beam-spin-angle: 135deg;
  }
  to {
    --border-beam-spin-angle: 495deg;
  }
}

/* The beam (`::before`) and its glow (`::after`) are two stacked rings
  occupying the same outer edge: the glow is wider and blurred, the beam is
  hairline and sharp. Both share `--border-beam-spin-angle` so the glow
  travels with the comet head with no gap. */
.animate-border-beam::before,
.animate-border-beam::after {
  content: "";
  position: absolute;
  inset: calc(-0.5 * var(--border-beam-width));
  border-radius: inherit;
  -webkit-mask:
    linear-gradient(#000 0 0) content-box,
    linear-gradient(#000 0 0);
  mask:
    linear-gradient(#000 0 0) content-box,
    linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  transition: opacity 350ms ease;
  pointer-events: none;
  animation: var(--border-beam-duration) linear var(--border-beam-delay, 0s) infinite
    var(--border-beam-direction) both border-spin;
}

/* The beam: a tight bright arc with a short fade, on an otherwise
  transparent ring. As `--border-beam-spin-angle` rotates, the bright spot
  travels around the perimeter like a comet. Stop positions scale with
  `--border-beam-arc-radius` (default 90deg) so the tail length is
  configurable while keeping the same relative shape. */
.animate-border-beam::before {
  padding: calc(0.5 * var(--border-beam-width));
  background: conic-gradient(
    from var(--border-beam-spin-angle),
    transparent 0deg,
    color-mix(in srgb, var(--border-beam-color) 90%, transparent)
      calc(var(--border-beam-arc-radius) * 0.222),
    var(--border-beam-color) calc(var(--border-beam-arc-radius) * 0.333),
    color-mix(in srgb, var(--border-beam-color) 60%, transparent)
      calc(var(--border-beam-arc-radius) * 0.556),
    transparent var(--border-beam-arc-radius),
    transparent 360deg
  );
  z-index: 2;
}

/* Glow ring: a 2px blurred conic that shares the beam's angle, so it forms
  a soft halo that overlaps the beam line directly — no gap. */
.animate-border-beam::after {
  padding: calc(0.5 * var(--border-beam-width) + 1px);
  background: conic-gradient(
    from var(--border-beam-spin-angle),
    transparent 0deg,
    color-mix(in srgb, var(--border-beam-color) 60%, transparent)
      calc(var(--border-beam-arc-radius) * 0.278),
    color-mix(in srgb, var(--border-beam-color) 35%, transparent)
      calc(var(--border-beam-arc-radius) * 0.556),
    transparent var(--border-beam-arc-radius),
    transparent 360deg
  );
  filter: blur(1.5px);
  z-index: 1;
}

@media (prefers-reduced-motion: reduce) {
  .animate-border-beam::before,
  .animate-border-beam::after {
    animation: none;
  }
}
</style>
