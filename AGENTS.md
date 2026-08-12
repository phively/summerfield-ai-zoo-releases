# Repository instructions

## Updating README.md

Update the root `README.md` catalog table only when the user explicitly requests a README update. Do not update it automatically before creating a commit.

### README catalog table

- Use the root `catalog.yaml` as the source of entries. For every item under `components`, copy its `name`, `type`, and `path` values exactly.
- Render the catalog `path` in the `Link` column as a relative Markdown link. For entries whose `type` is `skill`, link directly to `<path>/SKILL.md`; for example, render `skills/research-briefing` as `[skills/research-briefing](skills/research-briefing/SKILL.md)`. For entries whose `type` is `plugin`, continue to link to the plugin directory; for example, render `plugins/career-coach` as `[plugins/career-coach](plugins/career-coach)`.
- For entries whose `type` is `skill`, read the description from the YAML frontmatter `description` field in `<path>/SKILL.md`. Do not infer or rewrite it.
- For entries whose `type` is `plugin`, read the description from the `description` field in the plugin manifest. Look for `<path>/plugin.json`; if it is not present, use the standard Codex plugin location `<path>/.codex-plugin/plugin.json`. Do not infer or rewrite the description.
- For each plugin entry, recursively find every `SKILL.md` beneath `<path>/skills`. Under the plugin description in the same Description table cell, add a bulleted list containing each discovered skill. Use each skill's YAML frontmatter `name` as the list label and render it as a relative Markdown link directly to that `SKILL.md` file. Sort the list by relative path for deterministic output.
- Preserve the existing table columns, column order, header, separator row, and formatting when adding plugin descriptions and their skill lists. Represent each plugin skill list within its Description cell without splitting the catalog row into multiple Markdown table rows.
- Fail clearly and stop the README update if a catalog entry is missing `name`, `type`, or `path`; if a skill entry's `<path>/SKILL.md` is missing or has no frontmatter `description`; if a plugin entry has no plugin manifest or its manifest has no `description`; or if a discovered plugin `SKILL.md` has no frontmatter `name`.
- Render this Markdown table, preserving the column order:

  ```markdown
  | Name | Type | Link | Description |
  | --- | --- | --- | --- |
  | ... | ... | ... | ... |
  ```

- Wrap the generated table in `<!-- catalog:start -->` and `<!-- catalog:end -->` comments. On later updates, replace the complete marked block rather than adding a second table.
- The opening marker must be the first line of `README.md`. Preserve all README content below the closing marker.
- Replace line breaks inside cell values with spaces and escape Markdown table separators (`|`) with a backslash.
