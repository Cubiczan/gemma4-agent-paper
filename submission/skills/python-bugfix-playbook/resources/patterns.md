# Symptom -> where to look

- New option requested ("add a `foo` parameter"): add a keyword argument with a backward-compatible default to the public function AND thread it through every internal call path (sync and async variants, class __init__ and any factory/helper that builds it). Hidden tests usually call the public API with the new keyword.
- Wrong behaviour only for None / empty values: look for `if not x:` where `if x is None:` is meant, and for mutable default arguments.
- Async version behaves differently from sync: diff the two implementations side by side; the fix usually has to be mirrored in both.
- Validation/type errors (pydantic/typing): check how annotations are inspected (`Optional`, `Union`, `Annotated`, `X | None`) and whether the code handles both old- and new-style unions.
- Headers/encoding/URLs: check case-insensitivity, bytes vs str, percent-encoding, and that a default is not overwritten when the user supplied a value.
- Rendering/width/text layout: check cell width vs len(), trailing whitespace, wrapping at exact boundaries, and empty-input cases.
- Exceptions: when the issue says "should raise X", raise exactly that exception class with a message that includes the offending value.
- Deprecations: keep the old name working (alias) unless the issue says remove it.
