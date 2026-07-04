# Agent Skills for notion-agent-cli

Ready-made skills teaching an AI agent to drive Notion through the `notion`
CLI. Each is a directory with a `SKILL.md` following the
[Agent Skills](https://agentskills.io) open standard — portable to Claude Code
(as a plugin), and to any other agent that reads SKILL.md files or plain
markdown. No Claude-specific frontmatter is used.

| Skill | What / when |
|-------|-------------|
| [notion-shared](notion-shared/SKILL.md) | **Start here.** Auth, IDs, exit codes, `--data`, output modes — prerequisites for everything else. Includes a [troubleshooting reference](notion-shared/references/troubleshooting.md). |
| [notion-db](notion-db/SKILL.md) | Query, add, upsert, batch-import database rows. For structured data: tasks, trackers, CRM. |
| [notion-page](notion-page/SKILL.md) | Create/read/edit pages; full-page markdown read & write. For documents, notes, reports. |
| [notion-search](notion-search/SKILL.md) | Workspace search, blocks, comments, users. For finding things and resolving IDs. |
| [notion-schema-design](notion-schema-design/SKILL.md) | Create databases and evolve schemas, with the [exact JSON payload for every property type](notion-schema-design/references/property-shapes.md). |
| [notion-backup-sync](notion-backup-sync/SKILL.md) | Recipe: markdown ⇄ Notion publishing, backup to disk, restore. |
| [notion-knowledge-base](notion-knowledge-base/SKILL.md) | Recipe: build and maintain a tagged knowledge base. |
| [notion-task-tracker](notion-task-tracker/SKILL.md) | Recipe: run a task tracker — schema, queries, standup reports. |

## Install

**Claude Code** (plugin):

```
/plugin marketplace add henryreith/notion-cli
/plugin install notion-agent@notion-cli
```

**Any other agent**: `npm install -g notion-agent-cli`, set `NOTION_API_KEY`,
and point your agent at this directory — it also ships inside the npm package
at `node_modules/notion-agent-cli/skills/`. See the
[main README](../README.md#agent-skills-claude-and-any-other-agent) for details.

## Accuracy guarantee

Every `notion` command and flag documented in these skills is validated
against the actual CLI by `tests/unit/skills-docs.test.ts` in CI — the docs
cannot silently drift from the implementation.
