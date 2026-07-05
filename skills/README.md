# Agent Skills for notion-agent-cli

Ready-made skills teaching an AI agent to drive Notion through the `notion`
CLI. Each is a directory with a `SKILL.md` following the
[Agent Skills](https://agentskills.io) open standard — portable to Claude Code
(as a plugin) and to any other agent that reads SKILL.md files or plain
markdown: Codex, Cursor, or a personal/home agent like Hermes. Frontmatter
sticks to the portable spec fields (`name`, `description`, `license`,
`compatibility`, `metadata`) — nothing Claude-specific.

| Skill | What / when |
|-------|-------------|
| [notion-shared](notion-shared/SKILL.md) | **Start here.** Auth, IDs, exit codes, `--data`, output modes — prerequisites for everything else. Includes a [troubleshooting reference](notion-shared/references/troubleshooting.md). |
| [notion-db](notion-db/SKILL.md) | Query, add, upsert, batch-import database rows. For structured data: tasks, trackers, CRM. |
| [notion-page](notion-page/SKILL.md) | Create/read/edit pages; full-page markdown read & write. For documents, notes, reports. |
| [notion-search](notion-search/SKILL.md) | Workspace search, blocks, comments, users. For finding things and resolving IDs. |
| [notion-schema-design](notion-schema-design/SKILL.md) | Create databases and evolve schemas, with the [exact JSON payload for every property type](notion-schema-design/references/property-shapes.md). |
| [notion-reporting](notion-reporting/SKILL.md) | Rollups, weekly digests, standups, metrics — with a [jq cookbook for every property type](notion-reporting/references/extract-values.md). |
| [notion-capture](notion-capture/SKILL.md) | Quick capture for personal/home agents: inbox, link dedup, daily journal. |
| [notion-crm-pipeline](notion-crm-pipeline/SKILL.md) | Recipe: lightweight sales CRM — stages, upsert-by-email, stale-deal queries, activity log. |
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
at `node_modules/notion-agent-cli/skills/`. Copy the directories into your
agent's skill folder, or paste SKILL.md contents into its system prompt /
knowledge base. See the
[main README](../README.md#agent-skills-claude-and-any-other-agent) for details.

## Build your own skill

The CLI is the platform — these 11 skills are just the ones we ship. Any
workflow you can express as `notion` commands can be a skill. Minimal
template:

```markdown
---
name: my-workflow            # lowercase-hyphens, must match the directory name
description: What it does and when an agent should use it — include the words a user would actually say.
license: MIT
compatibility: Requires the notion CLI (npm i -g notion-agent-cli) and a Notion integration token (NOTION_API_KEY).
---

# My Workflow

Step-by-step instructions with real `notion` commands...
```

Rules that keep skills good (enforced by `npm test` for skills in this repo):

1. **Trigger-oriented description** — what + when + the keywords users say.
2. **Only real commands** — `tests/unit/skills-docs.test.ts` validates every
   `notion` command and flag in bash blocks against the actual CLI, and checks
   spec compliance (naming, description length, <500 lines).
3. **Heavy detail goes in `references/*.md`**, linked one level deep from
   SKILL.md, so agents load it only when needed.

Keep private/company-specific skills in your own repo or agent config;
generally useful ones are welcome as PRs here — the test suite reviews the
mechanical half automatically. The official spec validator also works:
`npx skills-ref validate skills/<name>` ([spec](https://agentskills.io/specification)).

## Accuracy guarantee

Every `notion` command and flag documented in these skills is validated
against the actual CLI by `tests/unit/skills-docs.test.ts` in CI — the docs
cannot silently drift from the implementation.
