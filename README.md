# Invoice Generator

[![CI](https://github.com/robbedchunk/invoice-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/robbedchunk/invoice-generator/actions/workflows/ci.yml)
[![CodeQL](https://github.com/robbedchunk/invoice-generator/actions/workflows/codeql.yml/badge.svg)](https://github.com/robbedchunk/invoice-generator/actions/workflows/codeql.yml)
[![Dependency Review](https://github.com/robbedchunk/invoice-generator/actions/workflows/dependency-review.yml/badge.svg)](https://github.com/robbedchunk/invoice-generator/actions/workflows/dependency-review.yml)

A lightweight HTTP server that generates professional PDF invoices from JSON payloads.
No database, no frontend; just send JSON and get a PDF.

## Quick Start

```bash
pip install -r requirements.txt
python -m invoice_generator
```

The server starts on `http://0.0.0.0:8080` by default.

## Usage

Send a `POST` request with a JSON body to `/`, `/invoice`, or `/generate`:

```bash
curl -X POST http://localhost:8080/invoice \
  -H "Content-Type: application/json" \
  -d @example.json \
  -o invoice.pdf
```

An example request body is included at [`example.json`](example.json).

### JSON Payload

```json
{
  "from": "Your Company Name",
  "to": "Client Name\n123 Main St\nCity, ST 12345",
  "number": "INV-001",
  "date": "2026-01-15",
  "items": [
    { "name": "Web Development", "quantity": 40, "unit_cost": 150.00 },
    { "name": "Design Work", "quantity": 10, "unit_cost": 120.00 }
  ],
  "notes": "Payment due within 30 days.\nThank you for your business!",
  "currency": "USD",
  "discounts": 10,
  "fields": { "discounts": "%" }
}
```

### Payload Fields

| Field | Type | Description |
|-------|------|-------------|
| `from` | string | Sender / company name |
| `to` | string | Recipient (newline-separated: name, address lines) |
| `number` | string | Invoice number |
| `date` | string | Invoice date |
| `items` | array | Line items (see below) |
| `notes` | string | Notes section (newline-separated) |
| `currency` | string | `USD`, `EUR`, or `GBP` (default: `USD`) |
| `discounts` | number | Discount amount or percentage |
| `fields.discounts` | string | Set to `%` for percentage discount |

Each item in `items`:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Item description |
| `quantity` | number | Quantity (default: 1) |
| `unit_cost` | number | Unit price |

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `INVOICE_HOST` | `0.0.0.0` | Server bind address |
| `INVOICE_PORT` | `8080` | Server port |
| `INVOICE_MAX_BODY_BYTES` | `268435456` | Maximum accepted request size in bytes |
| `INVOICE_MAX_PAGES` | `10000` | Maximum rendered page count before request is rejected |
| `INVOICE_MAX_CONCURRENT_RENDERS` | `min(32, CPU cores)` | Number of render worker processes |
| `INVOICE_MAX_INFLIGHT_RENDERS` | `max(100, workers*4)` | Maximum running + queued render jobs |
| `INVOICE_RENDER_QUEUE_TIMEOUT_MS` | `120000` | Wait time for queue slot before returning `503` |
| `INVOICE_RENDER_TIMEOUT_MS` | `300000` | Maximum render execution time before returning `504` |
| `INVOICE_LISTEN_BACKLOG` | `512` | TCP accept backlog size for burst traffic |
| `INVOICE_FONT_CACHE_DIR` | `/tmp/invoice-font-cache` | Base directory for per-worker font metric cache files |
| `INVOICE_FONT_PATH` | *(auto-detected)* | Path to a TTF font for Unicode support |
| `INVOICE_FONT_BOLD_PATH` | *(auto-detected)* | Path to bold TTF font variant |

Fonts are auto-detected on macOS and Linux. On Linux, install `fonts-dejavu` or `fonts-liberation` for best results:

```bash
# Debian/Ubuntu
sudo apt-get install fonts-dejavu-core

# RHEL/Fedora
sudo dnf install dejavu-sans-fonts
```

## Supported Versions

- Python: `3.10`, `3.11`, `3.12` (CI-tested)
- OS/runtime: Linux and macOS are supported for font auto-detection
- Windows: expected to work with explicit font paths via `INVOICE_FONT_PATH`/`INVOICE_FONT_BOLD_PATH`, but not CI-tested

## API Errors

The API returns JSON errors in the shape:

```json
{
  "error": "error_code",
  "detail": "Human-readable explanation"
}
```

Common responses:

| HTTP Status | `error` | When it happens |
|------------:|---------|-----------------|
| `400` | `invalid_content_length` | `Content-Length` is not an integer |
| `400` | `empty_body` | Body size is `0` bytes |
| `400` | `invalid_encoding` | Body is not valid UTF-8 |
| `400` | `invalid_json` | Body is not valid JSON |
| `400` | `invalid_payload` | Root JSON is not an object, or `items` is not an array |
| `404` | `not_found` | Unsupported route |
| `411` | `missing_content_length` | `Content-Length` header is missing |
| `413` | `payload_too_large` | Body exceeds `INVOICE_MAX_BODY_BYTES` |
| `413` | `invoice_too_large` | Estimated pages exceed `INVOICE_MAX_PAGES` |
| `503` | `server_busy` | Render queue is saturated |
| `503` | `render_pool_restarting` | Worker pool restarted; retry shortly |
| `504` | `render_timeout` | Render exceeded `INVOICE_RENDER_TIMEOUT_MS` |
| `500` | `render_failed` | Unexpected render failure |

## Features

- Modular package layout (`invoice_generator/`) with clear separation of concerns
- Framework-free HTTP API built on Python standard library
- Automatic multi-page layout for large invoices
- USD, EUR, GBP currency support
- Percentage or flat discount support
- Unicode text support with auto font detection (macOS + Linux)
- Threaded request handling

## Project Structure

```text
invoice_generator/
  __main__.py      # Runtime entrypoint
  server.py        # HTTP handlers and render worker orchestration
  rendering.py     # PDF invoice rendering engine
  formatting.py    # Text, money, date, and drawing helpers
  fonts.py         # Font discovery and FPDF font registration
  pagination.py    # Pagination estimation helpers
  config.py        # Environment-driven runtime configuration
  pdf_constants.py # Invoice layout/style constants
```

## Testing

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## Troubleshooting

- `Missing dependency 'fpdf'` on startup:
  Install dependencies with `pip install -r requirements.txt`.
- Invoice renders but text is missing/garbled:
  Ensure valid TTF fonts are available and, if needed, set `INVOICE_FONT_PATH` and `INVOICE_FONT_BOLD_PATH`.
- `server_busy` (`503`) under load:
  Increase `INVOICE_MAX_INFLIGHT_RENDERS` and/or `INVOICE_MAX_CONCURRENT_RENDERS` based on host capacity.
- `invoice_too_large` (`413`) for very large invoices:
  Increase `INVOICE_MAX_PAGES` or reduce line items per invoice.

## License

[MIT](LICENSE)
