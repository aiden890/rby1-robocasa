# Source and inspected video rules

Inspected on 2026-10-06 at lab-desktop. Source: `/home/aiden/Desktop/lab/robot/astra-robocasa/status-page`.

- `7306122e818158ac17bdfec57d3866c32546f039` (2026-10-06 15:47 +0900): clickable board and persistent recoverable deletion. Evidence: BOARD.md, assets/board.js, topic.js and `scripts/robocasa-astra/board_server.py`.
- `716814c452efd2490e0b99dc312fa15d54fd760d` (15:39 +0900): topic organization, multiple recordings, search, playback preservation. Evidence: README.md, topics.js, videos.js and topic.js.
- `210ea443851ab0573dd24d9efe0212061520f7f7` (15:32 +0900): source experiment recording/export at 20fps. This is source-specific methodology and is not asserted for new projects.

The source Git working tree was clean at inspection. This is the latest inspected version, not an automatic claim about future changes. Other candidates were the older RoboCasa Docker tracking page with additional task/skill tabs, and Online BC publish/review pages. The Astra status page directly matches the user's two-tab request and latest source updates.

Only code/style were reused. No topics/catalog data, research results, person-identifying UI labels, photos or video were copied. Branding and robot-specific descriptions became project configuration or explicit samples. The standalone server follows the same visibility-only deletion contract but binds loopback and validates item existence.
