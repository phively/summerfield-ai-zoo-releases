# Canonical recipe storage

`personal-chef` owns one Google Doc per canonical recipe and the workbook's `Recipe Catalog`. Use Google Drive discovery and the available Google Docs/Sheets skills for native reads, writes, preservation, and verification. Resolve the user's designated Meal Planning folder plus its `Recipes` and `Audits` subfolders by immutable IDs. Keep all planning records inside Meal Planning, recipe Docs inside Recipes, and migration or recovery artifacts inside a dated child folder under Audits. Preserve equivalent existing folder structure, file IDs, names, and sharing rather than creating duplicates.

Read [native artifact storage and formatting](../../../shared/artifact-formatting.md) before creating or formatting a recipe and use [the canonical recipe document template](recipe-document-template.md). Create native headings, tables, bulleted or numbered lists, and descriptive hyperlinks; never paste Markdown syntax or raw HTML into a Google Doc. Verify both document structure and every user-visible link after writing.

## Identity and contents

Give each recipe a stable `RC-...` ID. Catalog entries contain Recipe ID, Recipe name, Canonical Google Doc ID, a descriptive canonical recipe link, a descriptive original source link or original-recipe designation, Current version, Status, and Last updated. Store a raw URL only in a dedicated source or identity field when required for matching or routing; do not display it as a bare user-facing link. A catalog entry does not require a rating or a claim the recipe was made. Keep source attribution separate from the household Doc link.

The Doc contains the usable current recipe: a styled title; a native metadata table for recipe ID, status/version, yield, and times; named source attribution; a native ingredient table or formatted bulleted list; numbered instructions; headed sections for current adaptations, prep ahead, storage, leftovers, and unresolved details when applicable. Do not fabricate missing quantities, source facts, approval, or cooking outcomes. Preserve a legacy proposed recipe's proposed status during migration. Mark incomplete legacy recipes explicitly; they cannot become newly approved operational recipes until completed and reviewed.

Use Google Docs revision history for recipe edits. Retain concise historical preparation context in the Doc when it explains a rating or an earlier plan; do not maintain recipe instructions or modification logs in spreadsheet cells. Sheets may retain attributed outcome evidence, a version made, and a pointer to the relevant Doc section. A suggestion such as 'more salt' stays proposed with its unspecified quantity until the user confirms the change.

## Lifecycle

1. Resolve catalog and Doc identities before content writes. If titles match but sources or versions disagree, resolve the ambiguity; do not create a third authority.
2. During a pre-planning retrospective, save only user-confirmed reusable modifications and opinions. Preserve one-week deviations as preparation evidence rather than silently changing the canonical recipe.
3. Keep newly proposed plan recipes and adaptations transient until user approval. Once approved, create missing Google Docs in Recipes or edit existing canonical Docs in place. An explicit standalone request to save a recipe authorizes that bounded save without requiring a weekly plan.
4. Read back document content, native structure, identity, version, status, parent folder, and hyperlink targets before updating catalog and rating pointers. Reuse the returned ID on retries. A partial write must be reported with the successful and pending records; never describe a failed transaction as complete.
5. Pass verified named canonical recipe links and versions to the planner and shopper. Every finalized plan row links to its recipe; leftover rows link to the source dinner. Historical plans retain the version they used even though the file-level link opens the current recipe.
6. If a recipe change materially affects an already approved current plan, notify the planner and recompute affected quantities and costs only after the affected plan revision is approved.

Read current Docs and catalog rows by default; retrieve historical context only for a prior preparation, conflict, restoration, or explicit history request. Missing or inaccessible Docs do not justify a competing recipe authority. During cleanup, offer to bring recipe documents into the canonical native structure. Treat conversion from another file type or provider as a migration requiring explicit user permission and the staged audit in [the cleanup procedure](../../../shared/cleanup-migration.md). Provide clearly labeled pending changes and preserve existing state.
