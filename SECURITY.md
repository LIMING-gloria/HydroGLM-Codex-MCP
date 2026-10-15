# Security

## API keys

- Never commit an API key, credential file, or screenshot containing a key.
- Use `setup.sh` or `configure_key.py` to save a key locally.
- If a key is exposed, revoke it through the Hanhai platform and issue a replacement.
- Questions sent through this MCP are transmitted to the Hanhai API. Do not send data that must remain local.

## Reporting a problem

Do not include API keys in public issues. For API failures, share the timestamp, HTTP status, request ID (if returned), and sanitized error text with the API provider.
