import type { Tool } from "@/types/api"
import { atom } from "nanostores"

export const $tools = atom<Tool[]>([])
