# Vorratskammer – Home Assistant Integration

Custom integration that logs in to your Supabase-backed Vorratskammer app and exposes three sensors via your Edge Functions:

- `ha-inventory-summary`
- `ha-expiring-items` (`days` configurable)
- `ha-location-status`

## Install

### HACS (Custom Repo)

1. HACS → Integrations → ⋮ → Custom repositories
2. URL: `https://github.com/tobiasritscher/pantry-pal-ha` – Category: Integration
3. Install → Restart Home Assistant.

### Manual

Copy `custom_components/vorratskammer` into `/config/custom_components/`, then restart.

## Add integration

Settings → Devices & Services → **Add Integration** → search **Vorratskammer** → Provide:

- Supabase URL (e.g. `https://bscdbvbvylwqhkijhnub.supabase.co`)
- Email & Password (for your Vorratskammer account)
- Optional scan intervals and `days_ahead`

During setup you must provide:

- Supabase URL (e.g. https://...supabase.co)
- **Supabase Anon (public) API key**
- Email & Password

Tokens are stored and auto-refreshed.

## Entities

- `sensor.pantry_inventory_summary`
- `sensor.expiring_pantry_items`
- `sensor.pantry_locations`

These sensors mirror your function responses; attributes contain the payloads (items, counts, etc).

## Notes

- Auth via `POST /auth/v1/token?grant_type=password` and refresh via `grant_type=refresh_token`.
- On 401 from functions, the integration refreshes the token and retries once.
