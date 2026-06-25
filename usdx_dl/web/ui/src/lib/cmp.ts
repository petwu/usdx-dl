/**
 * Deeply compares two values for equality.
 */
export function deepEqual<T>(a: T, b: T): boolean {
  if (a === b) return true

  if (typeof a !== "object" || typeof b !== "object" || a === null || b === null) {
    return false
  }

  const keysA = Object.keys(a)
  const keysB = Object.keys(b)

  if (keysA.length !== keysB.length) return false

  // @ts-ignore
  return keysA.every((key) => deepEqual(a[key], b[key]))
}
