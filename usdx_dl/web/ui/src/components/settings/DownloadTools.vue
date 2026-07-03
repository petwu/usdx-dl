<script setup lang="ts">
import { Button } from "@/components/ui/button"
import { $setup } from "@/store/settings"
import { $tools, downloadTool } from "@/store/tools"
import { Check, Download } from "@lucide/vue"
import { useStore } from "@nanostores/vue"
import { computed, watch } from "vue"

const tools = useStore($tools)

const numMissing = computed(() => tools.value.filter((tool) => !tool.path).length)

watch(
  numMissing,
  (newVal) => {
    $setup.setKey("downloadTools", newVal === 0)
  },
  { immediate: true },
)
</script>

<template>
  <div class="prose max-w-none">
    <p>
      The app needs some external programs to work properly. Below you can see which
      ones are required and installed.
    </p>
    <p
      v-if="numMissing > 0"
      class="text-destructive border-destructive bg-destructive/10 rounded border px-3 py-2"
    >
      <strong
        >{{ numMissing }}
        {{ numMissing === 1 ? "tool is" : "tools are" }} missing.</strong
      >
      You need to install them before you can continue. Either install them manually on
      your system, make sure they are in your <code>PATH</code> and restart the app, or
      click the button below to download a prebuilt binary.
    </p>
    <ul class="not-prose">
      <li
        v-for="tool in tools"
        class="my-2 flex items-center justify-between rounded border px-2 py-1 leading-5 not-first:mt-2"
      >
        <div>
          {{ tool.name }}
          &nbsp; @ {{ tool.version ?? "unknown" }}<br />
          <span class="text-primary text-xs">{{ tool.path }}</span>
        </div>
        <Button v-if="!tool.path" size="icon" @click="downloadTool(tool.name)">
          <Download />
        </Button>
        <Check v-else class="text-success size-6" title="already installed" />
      </li>
    </ul>
  </div>
</template>
