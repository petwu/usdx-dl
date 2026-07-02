import { persistentJSON } from "@nanostores/persistent"

export type TabId =
  "tab-queue" | "tab-songs" | "tab-logs" | "tab-settings" | "tab-instructions"

export const $activeTab = persistentJSON<TabId>("tab:active", "tab-instructions")

export type AppPage = "page-main" | "page-setup"

export const $activePage = persistentJSON<AppPage>("page:active", "page-main")
