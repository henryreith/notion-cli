# Notion API Patterns Reference

Sourced from: `notion-sdk-py` (https://github.com/ramnes/notion-sdk-py), Notion REST API v2022-06-28.

---

## 1. Authentication & Required Headers

Every request to the Notion API must include:

```
Authorization: Bearer <integration_token_or_oauth_access_token>
Notion-Version: 2022-06-28
Content-Type: application/json
```

The SDK sets these on every request in `client.py` via the `httpx.Headers` block:

```python
client.headers = httpx.Headers({
    "Notion-Version": self.options.notion_version,  # "2022-06-28"
    "User-Agent": "ramnes/notion-sdk-py@3.0.0",
})
if self.options.auth:
    client.headers["Authorization"] = f"Bearer {self.options.auth}"
```

Base URL: `https://api.notion.com/v1/`

---

## 2. Property Payload Structures

When creating or updating a page's properties, the `properties` field is a map of
property name → property value object. The shape of the value object depends on the
property type.

### title

```json
{
  "title": [
    {
      "type": "text",
      "text": { "content": "My Title" }
    }
  ]
}
```

### rich_text

```json
{
  "rich_text": [
    {
      "type": "text",
      "text": { "content": "Some text" }
    }
  ]
}
```

Rich text supports optional annotations and a link:

```json
{
  "rich_text": [
    {
      "type": "text",
      "text": {
        "content": "Bold link text",
        "link": { "url": "https://example.com" }
      },
      "annotations": {
        "bold": true,
        "italic": false,
        "strikethrough": false,
        "underline": false,
        "code": false,
        "color": "default"
      }
    }
  ]
}
```

### select

```json
{
  "select": { "name": "Option Name" }
}
```

To clear: `{"select": null}`

### multi_select

```json
{
  "multi_select": [
    { "name": "Tag1" },
    { "name": "Tag2" }
  ]
}
```

### date

```json
{
  "date": {
    "start": "2024-01-15",
    "end": null
  }
}
```

With time and timezone:

```json
{
  "date": {
    "start": "2024-01-15T09:00:00.000Z",
    "end": "2024-01-15T17:00:00.000Z",
    "time_zone": "America/New_York"
  }
}
```

To clear: `{"date": null}`

### number

```json
{
  "number": 42
}
```

To clear: `{"number": null}`

### url

```json
{
  "url": "https://example.com"
}
```

To clear: `{"url": null}`

### checkbox

```json
{
  "checkbox": true
}
```

### relation

```json
{
  "relation": [
    { "id": "page-id-here" }
  ]
}
```

Multiple relations:

```json
{
  "relation": [
    { "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" },
    { "id": "ffffffff-0000-1111-2222-333333333333" }
  ]
}
```

### people

```json
{
  "people": [
    { "object": "user", "id": "user-id-here" }
  ]
}
```

### email

```json
{
  "email": "user@example.com"
}
```

### phone_number

```json
{
  "phone_number": "+1-555-867-5309"
}
```

### files

```json
{
  "files": [
    {
      "name": "attachment.pdf",
      "type": "external",
      "external": { "url": "https://example.com/attachment.pdf" }
    }
  ]
}
```

---

## 3. Full Page Create/Update Payload

### Create a page (POST /v1/pages)

```json
{
  "parent": { "database_id": "database-id-here" },
  "properties": {
    "Name": {
      "title": [{ "type": "text", "text": { "content": "Page Title" } }]
    },
    "Status": {
      "select": { "name": "In Progress" }
    },
    "Tags": {
      "multi_select": [{ "name": "design" }, { "name": "v2" }]
    },
    "Due Date": {
      "date": { "start": "2024-03-01", "end": null }
    },
    "Priority": {
      "number": 1
    },
    "Done": {
      "checkbox": false
    }
  },
  "children": []
}
```

### Update page properties (PATCH /v1/pages/{page_id})

```json
{
  "properties": {
    "Status": {
      "select": { "name": "Done" }
    },
    "Done": {
      "checkbox": true
    }
  }
}
```

---

## 4. Cursor-Based Pagination

All list/query endpoints are paginated. The pattern is consistent across every
endpoint that returns multiple results.

### Request parameters

- `page_size` (optional, int, max 100): Number of results per page. Defaults to 100.
- `start_cursor` (optional, string): Opaque cursor from the previous response's
  `next_cursor` field. Omit on the first request.

### Response shape

```json
{
  "object": "list",
  "results": [ /* array of objects */ ],
  "next_cursor": "fe2cc560-036c-44cd-90e8-294d5a74cebc",
  "has_more": true,
  "type": "page_or_database",
  "page_or_database": {}
}
```

- `has_more: true` means there are more pages of results.
- `next_cursor: null` when `has_more` is `false`.

### Python loop pattern (from helpers.py)

```python
def iterate_paginated_api(function, **kwargs):
    next_cursor = kwargs.pop("start_cursor", None)
    while True:
        response = function(**kwargs, start_cursor=next_cursor)
        for result in response.get("results"):
            yield result
        next_cursor = response.get("next_cursor")
        if not response.get("has_more") or not next_cursor:
            return
```

### Raw HTTP loop pattern

```python
import httpx

def fetch_all(url, headers, body):
    results = []
    start_cursor = None
    while True:
        payload = {**body}
        if start_cursor:
            payload["start_cursor"] = start_cursor
        resp = httpx.post(url, headers=headers, json=payload)
        data = resp.json()
        results.extend(data["results"])
        if not data.get("has_more") or not data.get("next_cursor"):
            break
        start_cursor = data["next_cursor"]
    return results
```

### Endpoints that support pagination

- `GET  /v1/blocks/{block_id}/children` — query params: `start_cursor`, `page_size`
- `POST /v1/databases/{database_id}/query` — body params: `start_cursor`, `page_size`
- `POST /v1/search` — body params: `start_cursor`, `page_size`
- `GET  /v1/users` — query params: `start_cursor`, `page_size`
- `GET  /v1/pages/{page_id}/properties/{property_id}` — query params for paginated property values

---

## 5. HTTP Status → Error Code Mappings

From `errors.py` (`APIErrorCode` enum):

| HTTP Status | Error Code String         | Meaning |
|-------------|--------------------------|---------|
| 400         | `invalid_json`           | Request body could not be decoded as JSON |
| 400         | `invalid_request_url`    | Request URL is not valid |
| 400         | `invalid_request`        | This request is not supported |
| 400         | `validation_error`       | Request body does not match expected schema |
| 401         | `unauthorized`           | Bearer token is not valid |
| 403         | `restricted_resource`    | Client does not have permission for this operation |
| 404         | `object_not_found`       | Resource does not exist or has not been shared with integration |
| 409         | `conflict_error`         | Transaction could not be completed (data collision) |
| 429         | `rate_limited`           | Too many requests; slow down and retry |
| 500         | `internal_server_error`  | Unexpected error; contact Notion support |
| 503         | `service_unavailable`    | Notion unavailable; retry later (also triggered when request exceeds 60s timeout) |

Client-side error codes (not from the API):

| Trigger | Error Code String                         | Meaning |
|---------|------------------------------------------|---------|
| Timeout | `notionhq_client_request_timeout`        | Request timed out before Notion responded |
| Unknown | `notionhq_client_response_error`         | API returned a non-standard error response |
| Path    | `notionhq_client_invalid_path_parameter` | Path parameter contains traversal sequences |

### Error response body shape

```json
{
  "object": "error",
  "status": 404,
  "code": "object_not_found",
  "message": "Could not find page with ID: ...",
  "request_id": "abc123"
}
```

---

## 6. Database Query Filter Structure

### POST /v1/databases/{database_id}/query

```json
{
  "filter": {
    "property": "Status",
    "select": {
      "equals": "In Progress"
    }
  },
  "sorts": [
    {
      "property": "Due Date",
      "direction": "ascending"
    }
  ],
  "page_size": 100
}
```

Compound filter (AND):

```json
{
  "filter": {
    "and": [
      { "property": "Done", "checkbox": { "equals": false } },
      { "property": "Priority", "number": { "less_than": 3 } }
    ]
  }
}
```

---

## 7. Block Content Payloads

Blocks are appended via `PATCH /v1/blocks/{block_id}/children`.

### Paragraph block

```json
{
  "object": "block",
  "type": "paragraph",
  "paragraph": {
    "rich_text": [{ "type": "text", "text": { "content": "Hello world" } }]
  }
}
```

### Heading blocks

```json
{ "type": "heading_1", "heading_1": { "rich_text": [{ "type": "text", "text": { "content": "H1" } }] } }
{ "type": "heading_2", "heading_2": { "rich_text": [{ "type": "text", "text": { "content": "H2" } }] } }
{ "type": "heading_3", "heading_3": { "rich_text": [{ "type": "text", "text": { "content": "H3" } }] } }
```

### Bulleted list item

```json
{
  "type": "bulleted_list_item",
  "bulleted_list_item": {
    "rich_text": [{ "type": "text", "text": { "content": "List item" } }]
  }
}
```

### To-do block

```json
{
  "type": "to_do",
  "to_do": {
    "rich_text": [{ "type": "text", "text": { "content": "Task description" } }],
    "checked": false
  }
}
```

### Code block

```json
{
  "type": "code",
  "code": {
    "rich_text": [{ "type": "text", "text": { "content": "print('hello')" } }],
    "language": "python"
  }
}
```

---

## 8. Search Endpoint

### POST /v1/search

```json
{
  "query": "search term",
  "filter": {
    "value": "page",
    "property": "object"
  },
  "sort": {
    "direction": "descending",
    "timestamp": "last_edited_time"
  },
  "page_size": 20,
  "start_cursor": null
}
```

`filter.value` can be `"page"` or `"database"`.

---

## 9. ID Format Notes

Notion IDs are UUIDs. The API accepts both:
- Formatted: `12345678-1234-1234-1234-123456789abc`
- Compact (no hyphens): `12345678123412341234123456789abc`

The SDK's `extract_notion_id()` normalises any URL or raw ID to the formatted
hyphenated form. When extracting from a URL, it prioritises the path segment
over query parameters so that database IDs are preferred over view IDs.

URL pattern: `https://notion.so/{workspace}/{page-title}-{32-char-hex-id}?v={view-id}`

---

## 10. SDK Client Options Reference

| Option           | Default                     | Description |
|------------------|-----------------------------|-------------|
| `auth`           | `None`                      | Bearer token |
| `timeout_ms`     | `60000`                     | Request timeout in milliseconds |
| `base_url`       | `"https://api.notion.com"`  | API root URL (override for mocking) |
| `log_level`      | `logging.WARNING`           | Python logging level |
| `logger`         | Console logger              | Custom `logging.Logger` instance |
| `notion_version` | `"2022-06-28"`              | Notion API version header value |

---

## 11. Key SDK Helper Functions

| Function | Purpose |
|----------|---------|
| `iterate_paginated_api(fn, **kwargs)` | Generator over all pages of a paginated endpoint |
| `collect_paginated_api(fn, **kwargs)` | Collect all paginated results into a list |
| `async_iterate_paginated_api(fn, **kwargs)` | Async generator version |
| `async_collect_paginated_api(fn, **kwargs)` | Async collect version |
| `is_full_page(response)` | True if response is a full Page object (has `url` field) |
| `is_full_block(response)` | True if response is a full Block object (has `type` field) |
| `is_full_database(response)` | True if response is a full Database object (has `title` field) |
| `is_full_user(response)` | True if response is a full User object |
| `get_url(object_id)` | Convert Notion object ID → `https://notion.so/{hex-id}` URL |
| `get_id(url)` | Extract ID from a Notion URL |
| `extract_notion_id(url_or_id)` | Extract and normalise any Notion ID or URL to hyphenated UUID |
| `extract_database_id(url)` | Alias of `extract_notion_id` for databases |
| `extract_page_id(url)` | Alias of `extract_notion_id` for pages |
| `extract_block_id(url)` | Extract block ID from URL fragment (`#block-...`) |
