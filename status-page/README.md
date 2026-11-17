# Research page template

Version 0.1.0. A separate static HTML/CSS/JavaScript template with only Main and Video tabs. Main is intentionally empty. The video board contains clearly labelled sample topics and empty recordings, not research results or copied media.

## Layout

- `template/`: shared pages, theme, topic board and player components.
- `project/config.json`: project title, tab list, refresh interval and recording note.
- `project/main.html`: project progress content, including commit and validation links.
- `project/data/`: topics and recording catalog. Replace samples with confirmed project data.
- `project/media/`: project-owned video/poster files, excluded from Git.
- `project/tabs/`: extra tabs when needed. Add a relative HTML path to config; Main and Video stay first.
- `scripts/`: build, loopback preview, reviewed local template update.
- `.runtime/`: private reversible board visibility state, excluded from build and Git.
- `dist/`: generated preview output only. Never serve the repository root.

## Build and preview

```sh
python3 scripts/build.py
python3 -m unittest discover -s tests -v
python3 scripts/serve.py --port 8910
```

Open http://127.0.0.1:8910 on the same host, or use a user-authorized SSH loopback tunnel. The server binds only loopback. This repository has no remote and is not deployed. The source project and its live server are preserved.

## Video behavior

The latest inspected source supports searchable topics, descriptions/tags, category/model/robot/task/outcome filters, ten-row pagination, a detail page with multiple recordings, unclassified runs, and refresh without replacing mounted video elements. Delete is a reversible visibility change, persisted outside the public directory; recording files are never removed. Same-origin requests and valid existing IDs are required.

Frame rate, timing interpretation, camera order and baseline comparability are project-specific metadata. The source's 20fps simulation claims are not universal template defaults. Empty sample records have no observed metrics or actual video. Add only confirmed recording information. Do not infer performance from samples.

## Reviewed updates

Keep project data, media, state and custom tabs in their project layer. Edit common files only when deliberately maintaining a template version. User changes to common files are detected and cause update refusal.

1. Save project work in Git and inspect status/diff. Review the new template source, VERSION.json and CHANGELOG.md.
2. Run `python3 scripts/update_template.py --source /path/to/reviewed/version` for a dry run.
3. If common files are unchanged, run the same command with `--apply`. It only copies manifest-listed common assets/scripts/version; it never writes `project/`, `.runtime/` or existing generated output.
4. Review Git diff, rebuild, run tests and browser checks, then commit within that project's authority. Do not automatically push, deploy or propagate to other projects.

For a template release, update VERSION.json and CHANGELOG.md, review changes, then run `python3 scripts/version_manifest.py` and tests. Do not refresh a consumer's manifest to conceal local customization. Resolve common-file conflicts manually with Git before applying an update. Project extensions are not overwritten.

The main page can link source commits, checks and next actions after project-specific content is provided. This template creates no Drive/ChatGPT page and grants no external sharing authority.
