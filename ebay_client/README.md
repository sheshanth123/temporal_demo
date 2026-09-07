# eBay Client

A small Python client for eBay's OAuth and Browse APIs.

## Requirements

- Python 3.11 or newer
- `uv`
- eBay API client ID and client secret

## Setup

From the project directory:

```powershell
uv sync
```

The project uses a `src` layout and the virtual environment is created in `.venv`.

## Environment

Create or update `.env` in the project root:

```env
EBAY_CLIENT_ID=your-client-id
EBAY_CLIENT_SECRET=your-client-secret
EBAY_BASE_URL=https://api.sandbox.ebay.com
```

Keep `.env` private. It is excluded from Git.

## Run

Run the application with:

```powershell
uv run ebay-client
```

Alternatively, use the virtual environment directly:

```powershell
.\.venv\Scripts\python.exe -m ebay_client.main
```

The application obtains an OAuth application token, searches for diamond listings, and prints details for the first result.

## SSL certificate issues

SSL verification is enabled by default. If your network uses a custom certificate authority, configure it in `.env`:

```env
EBAY_CA_BUNDLE=C:\path\to\company-ca.pem
```

For temporary troubleshooting only, disable verification for one PowerShell session:

```powershell
$env:EBAY_VERIFY_SSL = "false"
uv run ebay-client
```

Do not use disabled SSL verification in production.
