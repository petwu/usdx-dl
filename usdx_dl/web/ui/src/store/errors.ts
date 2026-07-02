import { $activeTab } from "@/store/nav"
import { atom } from "nanostores"

export const $errors = atom<string[]>([])

export async function addError(
  message: string,
  payload: Response | string | undefined = undefined,
) {
  let details: string | undefined = undefined
  if (!payload) {
  } else if (typeof payload === "string") {
    details = payload
  } else {
    if (payload.ok) {
      return
    }
    let details = payload.statusText
    const data = await payload.json()
    if (typeof data === "object" && "detail" in data) {
      if (typeof data.detail === "string") {
        details = data.detail
        if (/(usdb.+cookie|cookie.+usdb|PHPSESSID)/i.test(details)) {
          $activeTab.set("tab-settings")
        }
      } else if (Array.isArray(data.detail)) {
        details = data.detail
          .map((d: any) => {
            if (typeof d === "object" && d.type === "missing") {
              return `${d.msg} '${d.loc.join(".")}'`
            } else {
              return String(d)
            }
          })
          .join(", ")
      }
    }
  }
  const errors = $errors.get()
  if (details) {
    errors.push(`${message}: ${details}`)
  } else {
    errors.push(message)
  }
  $errors.set(errors)
}
