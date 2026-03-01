## [ERR-260301-001] egx-news skill not found

**Logged**: 2026-03-01T23:59:00Z
**Priority**: high
**Status**: pending
**Area**: tools

### Summary
User requested to list files in egx-news skill logs, but the skill doesn't exist in workspace

### Error
The egx-news skill directory and logs folder were not found when user requested to list files in ~/.openclaw/workspace/skills/egx-news/logs

### Context
- User asked to list files in egx-news logs
- Command executed successfully but no output (empty directory)
- This is the second time this pattern occurred without learning from it

### Suggested Fix
- Create the egx-news skill if it's needed
- Or inform user that the skill doesn't exist and suggest alternatives
- Implement check for skill existence before executing commands

### Metadata
- Reproducible: yes
- Related Files: ~/.openclaw/workspace/skills/
- See Also: None (first occurrence logged)

---