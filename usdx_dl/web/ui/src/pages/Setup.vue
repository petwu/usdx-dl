<script setup lang="ts">
import Button from "@/components/ui/button/Button.vue"
import { apiUrl } from "@/lib/host"
import { cn } from "@/lib/utils"
import { addError } from "@/store/errors"
import type { Tool } from "@/types/api"
import {
  AlertTriangle,
  Download,
  File,
  FileTerminal,
  Globe2,
  LoaderCircle,
} from "@lucide/vue"
import { ref } from "vue"

// backend state
const tools = ref<Tool[]>([])

// UI state
const inputDisabled = ref<boolean>(false)
const downloadingTools = ref<boolean>(false)

async function fetchTools() {
  const response = await fetch(apiUrl("/tools"))
  if (response.ok) {
    tools.value = await response.json()
  } else {
    await addError("Failed to fetch tools", response)
  }
}

async function autoDownloadTools() {
  downloadingTools.value = true
  inputDisabled.value = true
  const response = await fetch(apiUrl("/tools/download"), { method: "POST" })
  if (response.ok) {
    await fetchTools()
  } else {
    await addError("Failed to auto-download tools", response)
  }
  inputDisabled.value = false
  downloadingTools.value = false
}
</script>

<template>
  <main class="bg-destructive/10 flex h-dvh w-dvw items-center justify-center p-4">
    <div
      class="prose border-destructive bg-background flex h-fit max-h-full flex-col rounded border p-4"
    >
      <h2 class="text-destructive">
        <AlertTriangle class="-mt-1 mr-1 inline-block" />
        Missing Required Tools
      </h2>
      <div class="min-h-16 shrink grow overflow-y-auto">
        <p>
          The following required tools are missing. Please install them to continue. You
          can find installation instructions for each tool at the provided URL.
        </p>
        <p>
          If you have already installed the required tools, please make sure they are
          available in your system's <code>PATH</code> and restart the application.
        </p>
        <div v-for="tool in tools" class="my-8 flex gap-2">
          <div>
            <FileTerminal
              :class="cn('size-4', tool.version ? 'text-success' : 'text-destructive')"
            />
          </div>
          <div>
            <div class="leading-none">
              <strong :class="cn(tool.version ? 'text-success' : 'text-destructive')">
                {{ tool.name }}
              </strong>
              <span v-if="tool.version"> &nbsp; @{{ tool.version }}</span>
              <span v-else> &nbsp; (missing)</span>
            </div>
            <div class="*:text-muted-foreground mt-2 flex flex-col gap-2 text-sm">
              <a :href="tool.homepage" target="_blank" rel="noopener noreferrer">
                <Globe2 class="-mt-1 inline size-4" /> Homepage
              </a>
              <a :href="tool.downloadUrl" target="_blank" rel="noopener noreferrer">
                <Download class="-mt-1 inline size-4" /> Download (v{{ tool.latest }})
              </a>
              <span v-if="tool.version">
                <File class="-mt-1 inline size-4" /> {{ tool.path }}
              </span>
            </div>
          </div>
        </div>
      </div>
      <Button
        class="mt-8 w-full"
        :disabled="downloadingTools"
        @click="autoDownloadTools"
      >
        <Download v-if="!downloadingTools" />
        <LoaderCircle v-else class="animate-spin" />
        &nbsp; Auto-download all tools
      </Button>
    </div>
  </main>
</template>
