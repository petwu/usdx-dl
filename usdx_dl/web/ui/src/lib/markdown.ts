const rules: [RegExp, string | ((...args: string[]) => string)][] = [
  // headings
  [/^#{6}\s(.+)$/gm, "<h6>$1</h6>"],
  [/^#{5}\s(.+)$/gm, "<h5>$1</h5>"],
  [/^#{4}\s(.+)$/gm, "<h4>$1</h4>"],
  [/^#{3}\s(.+)$/gm, "<h3>$1</h3>"],
  [/^#{2}\s(.+)$/gm, "<h2>$1</h2>"],
  [/^#{1}\s(.+)$/gm, "<h1>$1</h1>"],
  // horizontal rule
  [/^---$/gm, "<hr />"],
  // bold & italic
  [/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>"],
  [/\*\*(.+?)\*\*/g, "<strong>$1</strong>"],
  [/\*(.+?)\*/g, "<em>$1</em>"],
  // strikethrough
  [/~~(.+?)~~/g, "<del>$1</del>"],
  // inline code
  [/`([^`]+)`/g, "<code>$1</code>"],
  // images
  [/!\[([^\]]*)\]\(([^)]+)\)/g, '<img alt="$1" src="$2" />'],
  // external links
  [
    /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>',
  ],
  // internal links
  [/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>'],
  // blockquote
  [/^&gt;\s(.+)$/gm, "<blockquote>$1</blockquote>"],
  // unordered list items
  [/^\s*[-*+]\s(.+)$/gm, "<li>$1</li>"],
  // ordered list items
  [/^\s*\d+\.\s(.+)$/gm, "<li>$1</li>"],
  // wrap consecutive <li> in <ul>
  [/(<li>.*<\/li>\n?)+/gs, (match) => `<ul>${match}</ul>`],
  // paragraphs (non-empty lines not already wrapped in a tag)
  [/^(?!<[a-z]).+$/gm, "<p>$&</p>"],
]

export function escapeHtml(input: string): string {
  return input.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
}

export function markdownToHtml(markdown: string): string {
  let html = escapeHtml(markdown)

  // Handle fenced code blocks before other rules
  html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (_, lang, code) => {
    const cls = lang ? ` class="language-${lang}"` : ""
    return `<pre><code${cls}>${code.trim()}</code></pre>`
  })

  for (const [pattern, replacement] of rules) {
    if (typeof replacement === "string") {
      html = html.replace(pattern, replacement)
    } else {
      html = html.replace(pattern, replacement)
    }
  }

  return html.trim()
}
