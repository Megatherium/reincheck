## **16\. Droid (Factory)**

*Factory.ai's agentic coding tool. High-autonomy capabilities.*

⚠️ **SECURITY WARNING:** The official installer pipes a script directly from a commercial URL (app.factory.ai) to sh. Inspect before running.

| Method | Install | Upgrade | Binary | Security/Notes |
| :---- | :---- | :---- | :---- | :---- |
| **Curl (Official)** | curl \-fsSL https://app.factory.ai/cli | sh | curl ... | sh (Idempotent) | droid | Source closed. Binary opaque. |
| **NPM** | None | \- | \- | \- |
| **Homebrew** | None | \- | \- | \- |
| **uv/Pip** | None | \- | \- | \- |
| **Mise** | None | \- | \- | \- |

## **17\. Goose (Block)**

*Block's (Square) open-source developer agent.*

⚠️ **SECURITY WARNING:** Downloads binaries from GitHub releases. Verify the release checksums if in a sensitive environment.

| Method | Install | Upgrade | Binary | Security/Notes |
| :---- | :---- | :---- | :---- | :---- |
| **Curl (Official)** | curl \-fsSL https://github.com/block/goose/releases/download/stable/download\_cli.sh | bash | goose update | goose | Checks GitHub releases. |
| **Homebrew** | brew install block-goose-cli | brew upgrade block-goose-cli | goose | **Safe Alternative.** Uses formulae. |
| **NPM** | None | \- | \- | \- |
| **uv/Pip** | None | \- | \- | \- |
| **Mise** | None | \- | \- | \- |

## **18\. Roo (Roo Code)**

*Roo Code (formerly Roo Cline). Primarily a VS Code Extension, not a standalone CLI.*

**Note:** Roo does not have a standalone binary like cline or goose yet. It runs within the VS Code host.

| Method | Install | Upgrade | Binary | Security/Notes |
| :---- | :---- | :---- | :---- | :---- |
| **VS Code CLI** | code \--install-extension RooVeterinaryInc.roo-cline | Auto-managed by VS Code | code | Extension runs in IDE. |
| **Curl** | None | \- | \- | \- |
| **NPM** | None (No CLI wrapper yet) | \- | \- | \- |
| **Homebrew** | None | \- | \- | \- |
| **uv/Pip** | None | \- | \- | \- |


