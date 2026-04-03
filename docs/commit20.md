
Commit 20: Backend-driven data lineage

- Added source_tracker to tag REAL/DUMMY for each variable
- Updated feature modules to attach *_source fields
- UI reads source via p[key + "_source"]
- No change to scores or rendering
