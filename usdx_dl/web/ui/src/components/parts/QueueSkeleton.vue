<script setup lang="ts">
import { Button } from "@/components/ui/button"
import { ButtonGroup } from "@/components/ui/button-group"
import { cn } from "@/lib/utils"
import {
  ArrowDown,
  ArrowDownToLine,
  ArrowUp,
  ArrowUpToLine,
  Pencil,
  Trash2,
} from "@lucide/vue"

const props = withDefaults(
  defineProps<{
    as?: string
    class?: string
  }>(),
  { as: "div" },
)
</script>

<template>
  <component
    :is="props.as"
    :class="
      cn(
        'bg-card overflow-hidden rounded border p-0',
        'grid grid-cols-[auto_1fr] grid-rows-[auto_auto] gap-2',
        'md:grid-cols-[auto_1fr_auto] md:grid-rows-[auto]',
        'animate-pulse',
        props.class,
      )
    "
    aria-hidden="true"
  >
    <div class="bg-muted size-24 shrink-0 rounded-br-lg" />
    <div class="grow">
      <h3 class="bg-muted w-4/5 rounded-md bg-clip-content py-0.5">&nbsp;</h3>
      <p class="bg-muted w-2/5 rounded-md bg-clip-content py-0.5 text-sm">&nbsp;</p>
      <p class="bg-muted w-3/5 rounded-md bg-clip-content py-0.5 text-sm">&nbsp;</p>
      <p>
        <a
          href="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
          target="_blank"
          rel="noopener noreferrer"
          class="bg-primary/50 inline-flex w-1/2 items-center gap-1 rounded-md bg-clip-content py-0.5 text-sm no-underline"
        >
          &nbsp;
        </a>
      </p>
    </div>
    <div
      class="flex flex-row justify-end max-md:col-span-2 md:col-start-3 md:row-start-1 md:mt-2 md:mr-2"
    >
      <ButtonGroup
        :class="
          cn(
            '*:disabled:*:opacity-25 *:disabled:opacity-100',
            '*:border-none max-md:*:first:rounded-tl-none max-md:*:last:rounded-br-none',
          )
        "
      >
        <Button size="icon" variant="outline" disabled>
          <ArrowUp />
        </Button>
        <Button size="icon" variant="outline" disabled>
          <ArrowDown />
        </Button>
        <Button size="icon" variant="outline" disabled>
          <ArrowUpToLine />
        </Button>
        <Button size="icon" variant="outline" disabled>
          <ArrowDownToLine />
        </Button>
      </ButtonGroup>
      <div class="grow md:w-4 md:grow-0"></div>
      <ButtonGroup
        :class="
          cn(
            '*:disabled:*:opacity-25 *:disabled:opacity-100',
            '*:border-none max-md:*:first:rounded-bl-none max-md:*:last:rounded-tr-none',
          )
        "
      >
        <Button size="icon" variant="outline" disabled>
          <Pencil />
        </Button>
        <Button size="icon" variant="destructive" disabled>
          <Trash2 />
        </Button>
      </ButtonGroup>
    </div>
  </component>
</template>
