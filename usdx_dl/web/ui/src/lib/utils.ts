import type { ClassValue } from "clsx"
import { clsx } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * Utility function that allows to conditionally render and merge TailwindCSS
 * classes without conflicts. Used heavily by shadcn.
 * @see https://dev.to/ramunarasinga/cn-utility-function-in-shadcn-uiui-3c4k
 * @example
 * ```vue
 * <template>
 *   <div :class="cn('text-base', { 'text-red-500': isRed }, props.class)">
 *     Hello World
 *   </div>
 * </template>
 *
 * <script setup lang="ts">
 * import { ref } from "vue"
 * import { cn } from "@/lib/utils"
 * const props = defineProps<{ class?: string }>()
 * const isRed = ref(Math.random() > 0.5)
 * </script>
 * ```
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Tagged template literal function to generate TailwindCSS classes.
 * This is just an identity function, but allows to configure the editor
 * and prettier to provide completions and formatting for string literals.
 * @see https://github.com/tailwindlabs/prettier-plugin-tailwindcss#sorting-classes-in-template-literals
 */
export function tw(strings: TemplateStringsArray, ...values: any[]) {
  return String.raw({ raw: strings }, ...values)
}
