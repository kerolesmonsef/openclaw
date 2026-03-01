## [LRN-260301-001] skill existence validation

**Logged**: 2026-03-01T23:59:00Z
**Priority**: medium
**Status**: pending
**Area**: tools

### Summary
Before executing commands on skill directories, validate that the skill actually exists

### Details
User requested to list files in egx-news logs multiple times, but the egx-news skill doesn't exist in the workspace. The command executed successfully but returned no output, indicating the directory was empty/non-existent.

### Suggested Action
Implement a validation step that checks if a skill directory exists before attempting to list its contents or execute commands within it.

### Metadata
- Source: user_feedback
- Related Files: ~/.openclaw/workspace/skills/
- Tags: validation, error_prevention
- Pattern-Key: validate.skill_existence
- Recurrence-Count: 2 (this is the second occurrence)
- First-Seen: 2026-03-01
- Last-Seen: 2026-03-01

---