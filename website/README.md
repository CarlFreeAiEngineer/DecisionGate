# Website

The public page at <https://ordinarydata.com/DecisionGate/>. It brags about the project and sends people to the repository; it does not list downloads.

- `index.html` deploys to `DecisionGate/index.html` on the server.
- `files-index.html` deploys to `DecisionGate/files/index.html`, so the folder holding the large release bundles shows a pointer to the repository instead of a directory listing.

The release bundles themselves live under `DecisionGate/files/<version>/` on the same server and are not in this repository; see [released/README.md](../released/README.md).

Deploy the pages alone with `uv run code/publish_released.py --site-only`, or together with a release using `--version X.Y.Z --site`. Both need SSH access to the web host. The pages are plain HTML with inline CSS and no build step; keep them that way.
