import { ref, watch } from "vue"

/**
 * Options for `sref()`.
 */
type SRefOptions = {
  /**
   * Whether the value should be persisted in `localStorage` or non-persisted
   * in `sessionStorage`.
   * @default true
   */
  persistent?: boolean
  /**
   * Controls whether the value is shared across the whole site (domain) or
   * unique to the current page.
   * @default "page"
   */
  scope?: "page" | "site"
  /**
   * Don't watch the storage value for changes.
   */
  noWatch?: boolean
}

/**
 * Create a reactive object that whose value is synced with either
 * `localStorage` or `sessionStorage`.
 *
 * Please avoid using this function for large objects or arrays, as it
 * will store the entire object as a JSON string in the storage.
 *
 * @param initValue The initial value of the reactive object.
 * @param key The storage key suffix. The full key is an implementation detail.
 * @param options Options controlling how the value is stored.
 *
 * @returns A reactive object that is synced with the respective storage.
 *
 * @example
 * ```typescript
 * const count = sref("count", 0)
 * const user = sref("user", { name: "John Doe", age: 30 })
 * const isDarkMode = sref("isDarkMode", false, { scope: "site" })
 * ```
 */
export function sref<T>(
  key: string,
  initValue: T | null = null,
  options: SRefOptions = {},
) {
  if (typeof window === "undefined") {
    throw Error("sref() can only be used in the browser")
  }
  if (key.length === 0) {
    throw Error("sref() requires a non-empty key")
  } else if (!/^[a-zA-Z0-9_:-]+$/.test(key)) {
    throw Error("sref() allows only [a-zA-Z0-9_:-] characters in the key")
  }

  const { persistent = true, scope = "page", noWatch = false } = options || {}

  const storage = persistent ? localStorage : sessionStorage
  const prefix = scope === "site" ? "" : location.pathname
  key = `sref://${prefix}#${key}`

  // create the ref object and initialize it with the stored value
  let value = initValue
  const storedValue = storage.getItem(key)
  if (storedValue !== null) {
    value = JSON.parse(storedValue)
  }
  const refObj = ref<T>(value as T)

  // watch the ref object and update the storage
  watch(
    refObj,
    (newValue) => {
      storage.setItem(key, JSON.stringify(newValue))
    },
    { deep: true },
  )

  // watch the storage and update the ref object
  if (!noWatch) {
    window.addEventListener(
      "storage",
      (event) => {
        if (event.key === key && refObj.value.toString() !== event.newValue) {
          refObj.value = JSON.parse(event.newValue!)
        }
      },
      { passive: true },
    )
  }

  return refObj
}
