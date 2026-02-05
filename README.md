# Invoice Generator

A lightweight HTTP server that generates professional PDF invoices from JSON payloads. No database, no frontend — just send JSON, get a PDF.

## Quick Start

```bash
pip install -r requirements.txt
python invoice_server.py
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
| `INVOICE_MAX_CONCURRENT_RENDERS` | `4` | Maximum simultaneous PDF renders |
| `INVOICE_RENDER_QUEUE_TIMEOUT_MS` | `45000` | Wait time for a render slot before returning `503` |
| `INVOICE_LISTEN_BACKLOG` | `512` | TCP accept backlog size for burst traffic |
| `INVOICE_FONT_CACHE_DIR` | `/tmp/invoice-font-cache` | Directory for font metric cache files |
| `INVOICE_FONT_PATH` | *(auto-detected)* | Path to a TTF font for Unicode support |
| `INVOICE_FONT_BOLD_PATH` | *(auto-detected)* | Path to bold TTF font variant |

Fonts are auto-detected on macOS and Linux. On Linux, install `fonts-dejavu` or `fonts-liberation` for best results:

```bash
# Debian/Ubuntu
sudo apt-get install fonts-dejavu-core

# RHEL/Fedora
sudo dnf install dejavu-sans-fonts
```

## Features

- Single-file server, no framework dependencies
- Automatic multi-page layout for large invoices
- USD, EUR, GBP currency support
- Percentage or flat discount support
- Unicode text support with auto font detection (macOS + Linux)
- Threaded request handling

## License

[MIT](LICENSE)
