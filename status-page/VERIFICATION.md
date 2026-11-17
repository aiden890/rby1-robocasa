# Verification (2026-10-06)

The template was created in a separate Git repository on lab-desktop. Python build and all template JavaScript syntax checks passed there. Six meaningful tests cover extension tabs/main content, invalid media paths, dry-run versus apply and preservation of every project file/media/private state, stopping for user-edited common files, refusing manifests that target project data, and persistent delete/restore plus rejected cross-origin API writes.

An actual browser inspected the lab-desktop preview through a loopback SSH tunnel. Verified: only Main and Video navigation tabs, empty Main, sample topic board, no-match search, multi-recording detail with no fabricated metrics, robot filtering, visibility deletion surviving reload, and restoration through trash. The sample topic was restored. No actual research media was copied, so playback continuity with a real media stream is not verified; mounted-player preservation follows the inspected source code and must be checked when project media is supplied. Ten-row pagination is retained in code but a multi-page dataset was not exercised in the browser.

The preview is temporary and loopback-only; no public deployment or Git remote exists. Source pages, data, recordings and experiments were not changed. Future latest-rule claims require reading the source and recording a new inspected commit.
