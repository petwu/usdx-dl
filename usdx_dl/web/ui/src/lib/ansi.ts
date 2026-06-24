const ANSI_COLORS: Record<number, string> = {
  // standard foreground colors
  30: "text-black",
  31: "text-red-500",
  32: "text-green-500",
  33: "text-yellow-500",
  34: "text-blue-500",
  35: "text-purple-500",
  36: "text-cyan-500",
  37: "text-white",
  // bright foreground colors
  90: "text-gray-500",
  91: "text-red-400",
  92: "text-green-400",
  93: "text-yellow-400",
  94: "text-blue-400",
  95: "text-purple-400",
  96: "text-cyan-400",
  97: "text-white",
  // standard background colors
  40: "bg-black",
  41: "bg-red-500",
  42: "bg-green-500",
  43: "bg-yellow-500",
  44: "bg-blue-500",
  45: "bg-purple-500",
  46: "bg-cyan-500",
  47: "bg-white",
  // bright background colors
  100: "bg-gray-500",
  101: "bg-red-400",
  102: "bg-green-400",
  103: "bg-yellow-400",
  104: "bg-blue-400",
  105: "bg-purple-400",
  106: "bg-cyan-400",
  107: "bg-white",
}

const ANSI_STYLES: Record<number, string> = {
  1: "font-bold",
  2: "opacity-50", // Dim
  3: "italic",
  4: "underline",
  9: "line-through",
}

/**
 * Converts a string containing ANSI escape codes into an HTML string
 * using Tailwind CSS utility classes for styling.
 *
 * @param input Raw string with ANSI escape sequences.
 * @returns HTML string with styled <span> elements.
 */
export function ansiToHtml(input: string): string {
  // Escape HTML special characters in a text node
  const escapeHtml = (str: string) =>
    str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")

  const ANSI_REGEX = /\x1b\[([0-9;]*)m/g

  let result = ""
  let lastIndex = 0
  let openSpans = 0
  let match

  while ((match = ANSI_REGEX.exec(input)) !== null) {
    // append any plain text before this escape sequence
    if (match.index > lastIndex) {
      result += escapeHtml(input.slice(lastIndex, match.index))
    }

    const codes = match[1].split(";").map(Number)
    const hasReset = codes[0] === 0 || match[1] === ""

    if (hasReset) {
      // close all open spans first
      result += "</span>".repeat(openSpans)
      openSpans = 0
    }

    const styleCodes = hasReset ? codes.slice(1) : codes
    const classes = styleCodes
      .map((code) => ANSI_COLORS[code] ?? ANSI_STYLES[code])
      .filter(Boolean)
      .join(" ")

    if (classes) {
      result += `<span class="${classes}">`
      openSpans++
    }

    lastIndex = ANSI_REGEX.lastIndex
  }

  // append any remaining plain text
  if (lastIndex < input.length) {
    result += escapeHtml(input.slice(lastIndex))
  }

  // close any unclosed spans
  result += "</span>".repeat(openSpans)

  return result
}
