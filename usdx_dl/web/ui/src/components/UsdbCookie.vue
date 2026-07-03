<script setup lang="ts">
import { Button } from "@/components/ui/button"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"
import { $setup } from "@/store/settings"
import { $usdbSessions, checkCookie, fetchUSDBSessions } from "@/store/usdb"
import { Check, ChevronDown, Info, PencilSparkles, RefreshCw, X } from "@lucide/vue"
import { useStore } from "@nanostores/vue"
import { ref, useId, watch, type HTMLAttributes } from "vue"

const props = withDefaults(
  defineProps<{
    disabled?: boolean
    open?: boolean
    class?: HTMLAttributes["class"]
  }>(),
  {
    disabled: false,
    open: false,
  },
)

const usdbSessions = useStore($usdbSessions)
const defaultOpen = ref(props.open ?? usdbSessions.value.length > 0)
watch(
  usdbSessions,
  (sessions) => {
    if (props.open === undefined) {
      defaultOpen.value = sessions.length > 0
    }
  },
  { once: true },
)

const model = defineModel<string | null>()
const valid = ref(false)
const id = useId()
const url = "https://usdb.animux.de"
const checking = ref(false)

watch(
  model,
  async (value) => {
    valid.value = !!value && !!(await checkCookie(value))
    $setup.setKey("usdbCookie", valid.value)
  },
  { immediate: true },
)

function checkAgain() {
  const tStart = performance.now()
  checking.value = true
  fetchUSDBSessions().finally(() => {
    const wait = 1000 - (performance.now() - tStart)
    setTimeout(() => (checking.value = false), Math.max(0, wait))
  })
}
</script>

<template>
  <section :class="cn('prose my-4 max-w-none', props.class)">
    <p>
      Some parts of the
      <a :href="url" target="_blank" rel="noopener noreferrer">USDB</a> site are only
      accessible to logged-in users. To make requests to USDB we need your
      <code>PHPSESSID</code> cookie for authentication.
    </p>
    <div class="my-4 flex items-center gap-2">
      <Label :for="id">USDB&nbsp;Cookie</Label>
      <Input
        v-model="model"
        :id="id"
        :disabled="props.disabled"
        placeholder="PHPSESSID=..."
      />
      <Check v-if="valid" class="text-success size-6" title="valid cookie" />
      <X v-else-if="model" class="text-destructive size-6" title="invalid cookie" />
    </div>
    <p class="flex items-center gap-2">
      <strong>Recommended: Automatically Detected Sessions</strong>
      <Button variant="default" size="xs" @click="checkAgain()" :disabled="checking">
        <RefreshCw :class="checking && 'animate-spin'" /> Check again
      </Button>
    </p>
    <template v-if="usdbSessions?.length">
      <div class="my-4 grid grid-cols-[repeat(auto-fill,minmax(15rem,1fr))] gap-2">
        <Button
          variant="outline"
          v-for="session in usdbSessions"
          :class="
            cn(
              'max-xs:w-full grid h-auto grid-cols-[auto_1fr] items-center gap-x-2 gap-y-0.5 text-start text-xs disabled:opacity-100',
              model === session.cookie ? 'border-success' : 'border-amber-500',
            )
          "
          :disabled="model === session.cookie"
          @click="model = session.cookie"
        >
          <Check v-if="model === session.cookie" class="text-success size-5" />
          <PencilSparkles v-else class="size-5 text-amber-500" />
          <span>{{ session.cookie }}</span>
          <div class="text-muted-foreground col-start-2">
            <i>from </i
            ><span class="text-primary capitalize">{{ session.browser }}</span>
          </div>
          <div class="text-muted-foreground col-start-2">
            <i> logged in as </i>
            <span class="bold text-secondary">{{ session.username }}</span>
          </div>
        </Button>
      </div>
    </template>
    <template v-else>
      <div class="text-muted-foreground flex items-center gap-1 text-sm italic">
        <Info class="size-4" /> No sessions found.
      </div>
      <p class="text-sm">
        The easiest way to get your USDB cookie is to simply open your browser, navigate
        to <a :href="url" target="_blank" rel="noopener noreferrer">{{ url }}</a> and
        login. In most cases the app is able to automatically extract the cookie from
        your browser.
      </p>
    </template>
    <p>
      <strong>Alternative: Manually Extract Cookie</strong>
    </p>
    <Collapsible
      class="col-span-2 overflow-hidden rounded border text-sm"
      :default-open="defaultOpen"
      v-slot="{ open }"
    >
      <CollapsibleTrigger
        :class="
          cn(
            'bg-muted flex w-full cursor-pointer items-center gap-2 px-2 py-1 marker:hidden',
            open && 'border-b',
          )
        "
      >
        <ChevronDown :class="cn('transition-transform', open && 'rotate-180')" />
        How to extract the PHPSESSID cookie?
      </CollapsibleTrigger>
      <CollapsibleContent as="ol">
        <li>
          Go to <a :href="url" target="_blank" rel="noopener noreferrer">{{ url }}</a
          >.
        </li>
        <li>Login to your account.</li>
        <li>Open the browser's developer tools, typically with <kbd>F12</kbd>.</li>
        <li>
          Run the following command in the console:
          <pre class="bg-muted my-0! mt-1 rounded p-2 text-sm whitespace-pre-wrap">
(await cookieStore.get("PHPSESSID")).value</pre>
        </li>
        <li>Copy the value and paste it into the above field.</li>
      </CollapsibleContent>
    </Collapsible>
  </section>
</template>
