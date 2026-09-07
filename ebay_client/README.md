# eBay Client

A Temporal-powered eBay Browse API pipeline.

## Requirements

- Python 3.11 or newer
- `uv`
- Temporal CLI (for the local Temporal server and Web UI)
- eBay API client ID and client secret

## Setup

From the project directory:

```powershell
uv sync
```

The project uses a `src` layout and the virtual environment is created in `.venv`.

## Start Temporal

The eBay client only prints the Temporal Web UI address; it does not start Temporal itself. Install the [Temporal CLI](https://docs.temporal.io/cli) and run this in a separate terminal:

```powershell
temporal server start-dev
```

Keep that terminal running. The Temporal Web UI will then be available at:

```text
http://localhost:8233
```

If you use Docker instead, start Docker Desktop first and run:

```powershell
docker run --rm -p 7233:7233 -p 8233:8233 temporalio/auto-setup:latest
```

## Environment

Create or update `.env` in the project root:

```env
EBAY_CLIENT_ID=your-client-id
EBAY_CLIENT_SECRET=your-client-secret
EBAY_BASE_URL=https://api.sandbox.ebay.com
TEMPORAL_UI_URL=http://localhost:8233
```

Keep `.env` private. It is excluded from Git.

## Run the pipelines

Start the worker in one terminal:

```powershell
uv run ebay-worker
```

Then trigger the workflows in a second terminal:

```powershell
temporal server start-dev
```

```powershell
uv run ebay-run
```

## SSL certificate issues

SSL verification is enabled by default. If your network uses a custom certificate authority, configure it in `.env`:

```env
EBAY_CA_BUNDLE=C:\path\to\company-ca.pem
```

For temporary troubleshooting only, disable verification for one PowerShell session:

```powershell
$env:EBAY_VERIFY_SSL = "false"
uv run ebay-run
```

Do not use disabled SSL verification in production.
