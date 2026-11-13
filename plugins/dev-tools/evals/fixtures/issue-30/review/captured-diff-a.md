# Captured diff A

Target identity: `sha256:fixture-snapshot-a` (synthetic label; the evaluation manifest carries the real file hash).

```diff
 def apply(items):
-    return []
+    return list(items)
```
