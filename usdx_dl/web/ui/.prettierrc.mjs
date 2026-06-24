/** @type {import("prettier").Config} */
export default {
  semi: false,
  quoteProps: "consistent",
  printWidth: 88,
  plugins: ["prettier-plugin-tailwindcss"],
  overrides: [
    {
      files: "*.astro",
      options: { parser: "astro" },
    },
  ],
  tailwindFunctions: ["clsx", "cva", "cn", "tw"],
}
