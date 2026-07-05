<script setup lang="ts">
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { markdownToHtml } from "@/lib/markdown"
import { cn } from "@/lib/utils"
import { $setup } from "@/store/settings"
import { $tools, downloadTool } from "@/store/tools"
import {
  Check,
  CloudDownload,
  Code,
  Download,
  Globe2,
  Hash,
  LoaderCircle,
  Package,
  Scale,
  X,
} from "@lucide/vue"
import { useStore } from "@nanostores/vue"
import { computed, ref, watch } from "vue"

const tools = useStore($tools)
const downloading = ref<Record<string, boolean>>({})
const showSha256 = ref<Record<string, boolean>>({})

const numMissing = computed(
  () => tools.value.filter((tool) => tool.downloadRequired).length,
)

watch(
  numMissing,
  (newVal) => {
    $setup.setKey("downloadTools", newVal === 0)
  },
  { immediate: true },
)

async function download(toolName: string) {
  downloading.value[toolName] = true
  try {
    await downloadTool(toolName)
  } finally {
    downloading.value[toolName] = false
  }
}
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
      <X class="-mt-1 mr-2 inline size-5" />
      <strong
        >{{ numMissing }}
        {{ numMissing === 1 ? "tool is" : "tools are" }} missing.</strong
      >
      You need to install them before you can continue. Either install them manually on
      your system, make sure they are in your <code>PATH</code> and restart the app, or
      click the button below to download a prebuilt binary.
    </p>
    <p
      v-else
      class="text-success border-success bg-success/10 rounded border px-3 py-2"
    >
      <Check class="-mt-1 mr-2 inline size-5" />
      <strong>All required tools are installed.</strong>
    </p>
    <ul class="not-prose">
      <li
        v-for="tool in tools"
        class="my-2 grid grid-cols-[1fr_auto] items-start gap-2 rounded border p-2 leading-5 not-first:mt-2"
      >
        <div>
          {{ tool.name }}
          <span v-if="tool.version" class="text-muted-foreground ml-2">
            v{{ tool.version }}
          </span>
        </div>
        <Transition name="fade">
          <X
            v-if="tool.downloadRequired"
            key="not-installed"
            class="text-destructive row-span-2 size-6"
            title="not installed"
          />
          <Check
            v-else
            key="installed"
            class="text-success row-span-2 size-6"
            title="already installed"
          />
        </Transition>
        <span
          :class="
            cn('text-xs', tool.downloadRequired ? 'text-destructive' : 'text-success')
          "
          >{{ tool.path }}</span
        >
        <div
          v-html="markdownToHtml(tool.reason)"
          class="text-muted-foreground col-span-2 text-sm"
        ></div>
        <div class="flex flex-wrap gap-1 text-xs *:no-underline">
          <Badge
            as="a"
            variant="outline"
            size="sm"
            :href="tool.homepage"
            target="_blank"
            rel="noopener noreferrer"
            title="homepage"
          >
            <Globe2 />
            {{ tool.homepage.replace(/https?:\/\//, "") }}
          </Badge>
          <Badge
            as="a"
            variant="outline"
            size="sm"
            :href="tool.repository"
            target="_blank"
            rel="noopener noreferrer"
            title="source code repository"
          >
            <Code />
            Repository
          </Badge>
          <template v-if="tool.downloadRequired">
            <Badge
              v-if="tool.provider"
              as="a"
              variant="outline"
              size="sm"
              :href="tool.provider"
              target="_blank"
              rel="noopener noreferrer"
              title="binary provider"
            >
              <CloudDownload />
              Provider
            </Badge>
            <Badge
              as="a"
              variant="outline"
              size="sm"
              :href="tool.downloadInfo.url"
              target="_blank"
              rel="noopener noreferrer"
              title="download link"
            >
              <Package />
              Download Link
            </Badge>
            <Badge
              as="button"
              variant="outline"
              size="sm"
              @click="showSha256[tool.name] = !showSha256[tool.name]"
              title="show cryptographic hash (SHA256)"
            >
              <Hash />
              SHA256
            </Badge>
            <Badge
              as="a"
              variant="outline"
              size="sm"
              :href="tool.licenseUrl"
              target="_blank"
              rel="noopener noreferrer"
              title="license"
            >
              <Scale />
              {{ tool.license }}
            </Badge>
          </template>
        </div>
        <div
          v-if="showSha256[tool.name] && tool.downloadRequired"
          class="text-muted-foreground col-span-2 text-xs wrap-anywhere"
          title="SHA256 checksum"
        >
          {{ tool.downloadInfo.sha256 }}
        </div>
        <Button
          v-if="tool.downloadRequired"
          class="col-span-2 w-full"
          :disabled="Object.values(downloading).some((v) => v)"
          @click="download(tool.name)"
        >
          <LoaderCircle v-if="downloading[tool.name]" class="mr-2 animate-spin" />
          <Download v-else />
          Download {{ tool.name }} v{{ tool.downloadInfo.version }}
        </Button>
      </li>
    </ul>
  </div>
</template>

<style scoped>
/**
 * <TransitionGroup> transitions
 * https://vuejs.org/guide/built-ins/transition-group
 */
.fade-enter-active,
.fade-leave-active {
  transition: all 0.5s ease-in-out;
}
.fade-enter-from {
  position: absolute;
  transform: scale(1.5);
}
.fade-leave-to {
  position: absolute;
  opacity: 0;
  transform: scale(0.5);
}
</style>
