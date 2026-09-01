// Custom markdownlint rule to ban em-dashes ('—') and replace with '--'
// See: https://github.com/DavidAnson/markdownlint/blob/main/doc/CustomRules.md

module.exports = {
  names: ["no-em-dashes", "no-em-dash"],
  description: "Em-dashes ('—') are not allowed; use '--' instead",
  tags: ["style", "typography"],
  parser: "none",
  function: function rule(params, onError) {
    params.lines.forEach((line, lineIndex) => {
      const regex = /—/g;
      let match;
      while ((match = regex.exec(line)) !== null) {
        const column = match.index + 1;
        onError({
          lineNumber: lineIndex + 1,
          detail: "Found em-dash ('—'); replace with '--'",
          context: line,
          range: [column, 1],
          fixInfo: {
            editColumn: column,
            deleteCount: 1,
            insertText: "--"
          }
        });
      }
    });
  }
};
