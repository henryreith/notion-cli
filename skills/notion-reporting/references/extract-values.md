# Extracting property values from Notion JSON with jq

`notion db query --output json` and `notion page get` return full Notion API
page objects. Every property type nests its value differently — these are the
exact jq paths. All examples assume a page object `.` (inside `.[]` when
iterating query results) and default to a safe fallback so missing values
don't crash the pipeline.

## Contents

- [Cheat sheet — every type](#cheat-sheet--every-type)
- [Flatten a whole row](#flatten-a-whole-row)
- [Filtering in jq (post-query)](#filtering-in-jq-post-query)
- [Gotchas](#gotchas)

## Cheat sheet — every type

```jq
# title → string
.properties.Name.title[0].plain_text // "Untitled"

# rich_text → string (join multi-segment text)
[.properties.Notes.rich_text[].plain_text] | join("")

# select → option name
.properties.Status.select.name // ""

# status → option name
.properties.Status.status.name // ""

# multi_select → array of names / comma string
[.properties.Tags.multi_select[].name]
[.properties.Tags.multi_select[].name] | join(",")

# number → number
.properties.Value.number // 0

# date → start date string (dates can have .start and .end)
.properties["Due Date"].date.start // ""

# checkbox → boolean
.properties.Done.checkbox

# people → array of user ids / names
[.properties.Assignee.people[].id]
[.properties.Assignee.people[].name]

# relation → array of related page ids
[.properties.Project.relation[].id]

# url / email / phone_number → string
.properties.Link.url // ""
.properties.Email.email // ""
.properties.Phone.phone_number // ""

# formula → value lives under its result type
.properties.Overdue.formula.boolean
.properties.Total.formula.number
.properties.Label.formula.string

# rollup → same idea: number | array | date under .rollup
.properties["Total Cost"].rollup.number

# created_time / last_edited_time → ISO string
.properties.Created.created_time
.properties.Edited.last_edited_time

# unique_id → prefix + number
"\(.properties.ID.unique_id.prefix)-\(.properties.ID.unique_id.number)"

# page metadata (not properties)
.id
.url
.created_time
.last_edited_time
```

Property names with spaces need bracket syntax: `.properties["Due Date"]`.

## Flatten a whole row

Turn a page object into a simple `{column: value}` record — useful before
CSV export or feeding another tool:

```bash
notion db query <db-id> --page-all --output json | jq '[.[] | {
  id: .id,
  name: (.properties.Name.title[0].plain_text // "Untitled"),
  status: (.properties.Status.select.name // ""),
  tags: ([.properties.Tags.multi_select[].name] | join(",")),
  value: (.properties.Value.number // 0),
  due: (.properties["Due Date"].date.start // "")
}]'
```

## Filtering in jq (post-query)

Prefer `--filter` (server-side) when the operator exists; drop to jq for
what the CLI filter syntax can't express (people matching, relation
contents, compound OR-of-ANDs):

```bash
# Pages assigned to a specific user
notion db query <db-id> --page-all --output json \
  | jq --arg uid "$MY_ID" '[.[] | select(any(.properties.Assignee.people[]?; .id == $uid))]'

# Pages related to a specific project page
notion db query <db-id> --page-all --output json \
  | jq --arg pid "<project-page-id>" '[.[] | select(any(.properties.Project.relation[]?; .id == $pid))]'
```

## Gotchas

- **Empty properties**: a select with no value is `"select": null` — always
  add `// fallback` before piping into string interpolation.
- **Multi-segment rich text**: bold/linked spans split the text into multiple
  array items; join them (`[.rich_text[].plain_text] | join("")`), don't take `[0]`.
- **Title property name varies**: it's whatever the database calls it (`Name`,
  `Task`, …). Find it with `notion db schema <db-id> --output properties`.
- **Hyphenless vs hyphenated IDs**: JSON responses contain hyphenated UUIDs;
  the CLI accepts either form as input.
