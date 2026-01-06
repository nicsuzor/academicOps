// Custom markdownlint rule to ban horizontal line dividers (H39)
// See: https://github.com/DavidAnson/markdownlint/blob/main/doc/CustomRules.md

module.exports = {
  names: ["no-horizontal-rules", "H39"],
  description: "Horizontal line dividers are not allowed",
  tags: ["hr", "style"],
  parser: "markdownit",
  function: function rule(params, onError) {
    // Find all thematic break (horizontal rule) tokens
    for (const token of params.parsers.markdownit.tokens) {
      if (token.type === "hr") {
        onError({
          lineNumber: token.lineNumber,
          detail: "Use headings for structure instead of horizontal lines (---, ***, ___)",
          context: token.line
        });
      }
    }
  }
};
