# Native artifact storage and formatting

Read this reference before creating a canonical Meal Planner artifact, formatting one during cleanup, or proposing a file-type migration. Preserve an existing authoritative file, provider ID, folder, sharing configuration, and compatible structure unless the user authorizes a change.

## Storage preference

When creating a new canonical artifact and the user has not selected another location or format:

1. Prefer the user's accessible Google Drive and resolve the designated `Meal Planning` folder by immutable ID.
2. Use Google Sheets for structured household, preference, rating, grocery, and catalog records. Use Google Docs for narrative meal plans and recipes so they retain native editing and revision history.
3. Create or reuse the `Recipes` subfolder for canonical recipe Docs and the `Audits` subfolder for audit, compaction, migration, and recovery artifacts. Resolve each folder by immutable ID before writing.
4. Preserve a clearly equivalent existing folder, including an established singular or differently named folder, instead of creating a duplicate or renaming it without authorization.
5. If Drive or the required native editor is unavailable, use one user-selected durable fallback and disclose the limitation. Do not create several formats as competing authorities.

Keep each audit operation in a dated child folder under `Audits`, such as `Migration audit YYYY-MM-DD` or `Compaction audit YYYY-MM-DD`. Append local time when needed for uniqueness. Never treat a file in `Audits` as the current authority.

## Native structure

- In Google Docs, create real heading styles, paragraphs, bulleted or numbered lists, and native tables. Do not paste Markdown headings, list markers, table pipes, or raw HTML as document content.
- In Google Sheets, use actual cells, header formatting, filters or native tables when supported, named ranges, data validation, wrapping, and suitable column widths. Do not put a Markdown table into one cell or use Markdown as a substitute for worksheet structure.
- In other formats, use that format's native heading, list, table, and hyperlink features when available. A text-only fallback may use Markdown, but it remains a fallback rather than a model for Google artifacts.
- Read back consequential content and inspect the resulting structure after writing. A write is incomplete when the correct text exists but required headings, lists, tables, or links were not created in native form.

## Links

Every user-visible link must have concise descriptive display text, use the artifact's native hyperlink or supported smart-chip representation, and resolve to the intended resource before publication. Do not present a bare URL or raw HTML as the link label. Keep immutable resource IDs and raw URLs only in dedicated identity or source fields when required for reliable routing; they do not replace the named user-visible link.

When a target is pending or inaccessible, label the link as pending or unresolved instead of inventing a URL or claiming verification. After a migration or authority transfer, update dependent links only after the replacement resource and its content have been verified.

## Cleanup formatting and file-type migration

During cleanup, inspect canonical artifacts against their defined structure and offer useful formatting corrections. Examples include applying recipe headings, converting literal Markdown into native document elements, turning household ranges into formatted native tables, adding validation, and repairing named links. Perform an in-place formatting change only when it is within the authorized cleanup scope, and preserve content, stable identities, formulas, validations, provenance, and sharing.

Treat conversion between file types or providers as a proposed migration, including Excel to Google Sheets and Word or Markdown to Google Docs. Obtain the user's explicit permission before creating the replacement as part of a migration, transferring canonical authority, retiring the original, or changing dependent links. Before an approved conversion:

1. Explain the source, proposed target format and location, benefits, affected IDs or links, and recovery plan.
2. Preserve the original in the dated `Audits` child folder or retain an equally recoverable native revision.
3. Convert into a staged replacement and validate content plus native structure.
4. Reconfirm concurrent source state, then transfer authority and update pointers only after the audit passes.
5. Leave the original authority unchanged when permission is absent or validation fails.
