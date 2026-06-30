<script setup lang="ts">
import Logo from "#/logo.svg"
import { Input } from "@/components/ui/input"
import { TabLink } from "@/components/ui/tabs"
import { cn } from "@/lib/utils"
import {
  ArrowDown,
  ArrowUp,
  Folder,
  Pause,
  Pencil,
  Play,
  SendHorizontal,
  Trash2,
} from "@lucide/vue"
import type { HTMLAttributes } from "vue"

const props = defineProps<{
  class?: HTMLAttributes["class"]
}>()
</script>

<template>
  <div
    :class="
      cn(
        'prose',
        'bg-card max-w-none rounded border p-4 text-justify',
        '[&_svg]:mb-0.5 [&_svg]:inline [&_svg]:size-4',
        props.class,
      )
    "
  >
    <img
      :src="Logo"
      alt=""
      class="mb-4 size-32 max-sm:mt-8 max-sm:block max-sm:w-full sm:float-left sm:mr-8"
    />
    <h2 class="mt-0 max-sm:text-center">usdx-dl</h2>
    <p>
      <!-- cSpell: disable-next-line -->
      An app to <b>d</b>own<b>l</b>oad songs in the <b>U</b>ltra<b>S</b>tar
      <b>D</b>elu<b>x</b>e (<a
        href="https://usdx.eu"
        target="_blank"
        rel="noopener noreferrer"
        >usdx.eu</a
      >) format for SingStar&trade;-like karaoke games. Uses
      <a
        href="https://github.com/yt-dlp/yt-dlp"
        target="_blank"
        rel="noopener noreferrer"
        class="whitespace-nowrap"
        >yt-dlp</a
      >
      to download the audio and video from YouTube and then applies various AI models to
      split the vocals and music or even transcribe the lyrics and generate the
      <code>.txt</code> song file in the proper
      <a href="https://usdx.eu/format/" target="_blank" rel="noopener noreferrer"
        >format</a
      >.
    </p>

    <h3 class="clear-both">Finding Songs</h3>
    <p><strong>✨ Recommended: USDB</strong></p>
    <p>
      Go to
      <a href="https://usdb.animux.de/" target="_blank" rel="noopener noreferrer"
        >usdb.animux.de</a
      >, login or create an account, search for the song you want to download and copy
      the URL with the <code>id=...</code> parameter, e.g.:
    </p>
    <pre>https://usdb.animux.de/?link=detail&id=1368</pre>
    <p>
      This (typically) gives high-quality lyrics that are in sync with the music and
      manually annotated pitch information for the vocals.
    </p>
    <p><strong>Alternative: YouTube</strong></p>
    <p>
      Search any song on
      <a href="https://www.youtube.com/" target="_blank" rel="noopener noreferrer"
        >YouTube</a
      >
      and copy the video URL, e.g.:
    </p>
    <pre>https://www.youtube.com/watch?v=dQw4w9WgXcQ</pre>
    <p>
      With YouTube videos, we need to use AI models to transcribe the lyrics and
      generate the pitch information and usdx <code>.txt</code> files, which may not be
      as accurate as the USDB source. It is also slower.
    </p>

    <h3>Managing the Queue</h3>
    <p>
      After you found the URL to the song you want to download, paste it into the
      <Input
        placeholder="input field"
        class="inline-block h-8 w-28 opacity-100!"
        disabled
      />
      at the top of the app and click the submit button <SendHorizontal /> or press
      <kbd>Enter</kbd>. This will add the song to the processing
      <TabLink id="tab-queue">Queue</TabLink> and ask you to verify and, if necessary,
      edit <Pencil /> the song metadata.
    </p>
    <p>
      You can move songs up <ArrowUp /> or down <ArrowDown /> in the queue to prioritize
      them, or remove <Trash2 /> them if you change your mind. The queue is processed in
      order from top to bottom.
    </p>

    <h3>Viewing Songs</h3>
    <p>
      The
      <TabLink id="tab-songs">Songs</TabLink>
      tab displays all downloaded songs. You can filter them by title or artist, play
      <Play /> the audio track and open the song folder <Folder /> in your file
      explorer.
    </p>

    <h3>Viewing Output Logs</h3>
    <p>
      The <TabLink id="tab-output">Output</TabLink> tab shows real-time logs of the
      worker processing the queue. Processing a single song typically takes a few
      minutes, depending on the length of the song and the speed of your computer. You
      can pause <Pause /> or resume <Play /> processing with the button in the top left.
      If a problem occurs, the logs probably contain useful error messages.
    </p>

    <h3>Settings</h3>
    <p>
      The <TabLink id="tab-settings">Settings</TabLink> tab allows you to configure
      various options for the tool, e.g. which AI models to use for individual tasks.
    </p>
  </div>
</template>
