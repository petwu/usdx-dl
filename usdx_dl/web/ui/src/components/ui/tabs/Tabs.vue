<script setup lang="ts">
import { cn } from "@/lib/utils"
import { onMounted, onUnmounted, provide, ref, watch, type HTMLAttributes } from "vue"

const props = defineProps<{
  defaultTab?: string
  class?: HTMLAttributes["class"]
  history?: boolean
  titleTemplate?: string
  unmountOnHide?: boolean
}>()

const activeTab = defineModel<string>({ default: "" })
if (!activeTab.value && props.defaultTab) {
  activeTab.value = props.defaultTab
}
const mounted = ref(false)
const skipNextHistoryPush = ref(false)
const unmountOnHide = ref(props.unmountOnHide ?? false)

function setTab(id: string, text?: string) {
  activeTab.value = id
  if (props.titleTemplate) {
    document.title = props.titleTemplate
      .replace("{tab}", text ?? "")
      .replace(/^[\s-]+|[\s-]+$/g, "")
  }
}

function checkName(id: string) {
  if (props.history && id && !/^tab-[\w-]+$/.test(id)) {
    throw new Error(
      "Tab id must be in the format of 'tab-{name}' when history is enabled.",
    )
  }
}

function nameToHash(id: string) {
  return `#${id.replace(/^tab-/, "")}`
}

function hashToName(hash: string) {
  return `tab-${hash.replace(/^#/, "")}`
}

if (props.history) {
  checkName(props.defaultTab || "")
  checkName(activeTab.value || "")
}

provide("activeTab", activeTab)
provide("unmountOnHide", unmountOnHide)
provide("setTab", setTab)

watch(
  () => activeTab.value,
  (newValue) => {
    checkName(newValue || "")
    if (props.history && mounted.value && !skipNextHistoryPush.value && newValue) {
      history.pushState(null, "", nameToHash(newValue))
    }
  },
  { immediate: true },
)

function onHashChange() {
  if (window.location.hash) {
    skipNextHistoryPush.value = true
    activeTab.value = hashToName(window.location.hash)
  }
}

onMounted(() => {
  if (props.history) {
    if (window.location.hash) {
      activeTab.value = hashToName(window.location.hash)
    } else {
      history.replaceState(null, "", nameToHash(activeTab.value || ""))
    }
    window.addEventListener("hashchange", onHashChange)
  }
  mounted.value = true
})
onUnmounted(() => {
  if (props.history) {
    window.removeEventListener("hashchange", onHashChange)
  }
})
</script>

<template>
  <div :class="cn('flex flex-col gap-2', props.class)">
    <slot />
  </div>
</template>
