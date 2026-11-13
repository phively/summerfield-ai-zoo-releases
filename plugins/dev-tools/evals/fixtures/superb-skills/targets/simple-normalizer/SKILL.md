---
name: fixture-simple-normalizer
description: Fixture target for one deterministic filename normalization.
---

When the user supplies a filename, lowercase it, replace runs of non-alphanumeric characters with one hyphen, preserve the extension, and return the result. Do not store preferences or benchmark the transformation.
