# Deployment Guide

## PyPI Publication

### Manual
```bash
pip install build twine
python -m build
twine upload dist/*
```

### GitHub Actions (automated)
Push a version tag to trigger the publish workflow:
```bash
git tag v0.1.0
git push origin v0.1.0
```

## Installation

```bash
pip install notion-agent-cli
notion --version  # → 0.1.0
```

## Verify

```bash
export NOTION_API_KEY=secret_xxx
notion auth test       # {"status": "ok", ...}
notion --help          # all command groups
```

## Homebrew (future)

Homebrew formula template:
```ruby
class NotionAgentCli < Formula
  desc "Zero-overhead CLI for Notion API"
  homepage "https://github.com/henryreith/notion-agent-cli"
  url "https://files.pythonhosted.org/packages/.../notion-agent-cli-0.1.0.tar.gz"
  license "MIT"

  depends_on "python@3.12"

  def install
    system "pip3", "install", *std_pip_args, "."
  end

  test do
    system "#{bin}/notion", "--version"
  end
end
```
