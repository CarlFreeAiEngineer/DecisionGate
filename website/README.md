# Website

The public page at <https://62-84-178-253.sslip.io/DecisionGator/>. It brags about the project and sends people to the repository; it does not list downloads.

- `index.html` deploys to `DecisionGator/index.html` on the server.
- `try.html` deploys to `DecisionGator/try.html`: an editable, runnable JavaScript example. It imports the browser component from `files/<version>/web/index.js` on the same server (the version is written into the page; update it when publishing a new release) and quietly makes a first call at page load so the visitor's first Run does not wait for the 580 MB download. The web host sends `Cache-Control: no-store` for everything under `DecisionGator/`: browsers refetched the weights every visit anyway, and without a cache an update is live at once.
- `files-index.html` deploys to `DecisionGator/files/index.html`, so the folder holding the large release bundles shows a pointer to the repository instead of a directory listing.

The release bundles themselves live under `DecisionGator/files/<version>/` on the same server and are not in this repository; see [released/README.md](../released/README.md).

Deploy the pages alone with `uv run code/publish_released.py --site-only`, or together with a release using `--version X.Y.Z --site`. Both need SSH access to the web host. The pages are plain HTML with inline CSS and no build step; keep them that way.

Style: when a phrase needs emphasis, SHOUT IT IN CAPS. Bold is barely noticeable and is reserved for the lead-in words of a paragraph or list item.
