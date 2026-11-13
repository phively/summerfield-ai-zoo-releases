# Current diff B

Target identity: `sha256:fixture-snapshot-b` (synthetic label; the evaluation manifest carries the real file hash).

```diff
 def apply(items):
-    return []
+    return [item for item in items if item.enabled]
```
