# Vorratskammer – Home Assistant Integration

Custom integration that logs in to your Supabase-backed Vorratskammer app and exposes four sensors via your Edge Functions:

- `ha-inventory-summary`
- `ha-expiring-items` (`days` configurable)
- `ha-location-status`
- `ha-location-items` (detailed items per location; provides `all_items_sorted` attribute)

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
- `sensor.pantry_location_items` (attributes include full location list + flattened `all_items_sorted`)

These sensors mirror your function responses; attributes contain the payloads (items, counts, etc).

## Notes

# Versioning

Integration version is tracked in `manifest.json` and exported as `__version__` in `const.py`.

- Auth via `POST /auth/v1/token?grant_type=password` and refresh via `grant_type=refresh_token`.
- On 401 from functions, the integration refreshes the token and retries once.

# App Docs (https://pantrypal.ritscher.ch | https://github.com/tobiasritscher/pantry-pal-webapp)

This section explains how to integrate your Vorratskammer pantry management app with Home Assistant to monitor inventory from your smart home dashboard.

## Available API Endpoints

The app provides four Home Assistant-compatible REST API endpoints:

### 1. Inventory Summary (`/functions/v1/ha-inventory-summary`)

Returns overall inventory statistics.

**Response format:**

```json
{
  "state": 45,
  "attributes": {
    "total_items": 45,
    "expiring_soon": 3,
    "freezer_items": 15,
    "dry_items": 25,
    "emergency_items": 5,
    "last_updated": "2025-01-27T10:30:00Z",
    "unit_of_measurement": "items"
  }
}
```

### 2. Expiring Items (`/functions/v1/ha-expiring-items`)

Returns detailed information about items expiring soon. **Note**: Date logic now prioritizes `verbrauchen_bis` (use by date) over `ablaufdatum` (expiry date) for more accurate expiry tracking.

**Query Parameters:**

- `days` (optional): Number of days ahead to check (default: 7)

**Response format:**

```json
{
  "state": 3,
  "attributes": {
    "items": [
      {
        "name": "Milch",
        "expires": "2025-01-29",
        "location": "Kühlschrank",
        "location_type": "freezer",
        "days_until_expiry": 2,
        "quantity": 1,
        "brand": "Alpro",
        "urgency": "critical"
      }
    ],
    "critical_items": 1,
    "warning_items": 2,
    "days_ahead": 7,
    "last_updated": "2025-01-27T10:30:00Z",
    "unit_of_measurement": "items"
  }
}
```

### 3. Location Status (`/functions/v1/ha-location-status`)

Returns status for all storage locations or a specific location.

**Query Parameters:**

- `location_id` (optional): Specific location UUID to query

**Response format (all locations):**

```json
{
  "state": 3,
  "attributes": {
    "total_locations": 3,
    "total_items_all_locations": 45,
    "locations": [
      {
        "id": "uuid",
        "name": "Kühlschrank",
        "type": "freezer",
        "total_items": 15,
        "expiring_items": 2,
        "utilization_percent": 30,
        "note": "Hauptkühlschrank",
        "last_restocked": 1706356800000
      }
    ],
    "last_updated": "2025-01-27T10:30:00Z",
    "unit_of_measurement": "locations"
  }
}
```

### 4. Location Items (`/functions/v1/ha-location-items`)

Returns detailed item information for each storage location. This endpoint provides comprehensive item listings rather than just status summaries, making it ideal for detailed monitoring of specific locations.

**Query Parameters:**

- `location_id` (optional): Specific location UUID to query

**Response format (all locations):**

```json
{
  "state": 3,
  "attributes": {
    "total_locations": 3,
    "locations": [
      {
        "id": "uuid",
        "name": "Kühlschrank",
        "type": "freezer",
        "note": "Hauptkühlschrank",
        "total_items": 15,
        "expiring_items": 2,
        "critical_items": 1,
        "warning_items": 1,
        "items": [
          {
            "name": "Milch",
            "quantity": 2,
            "brand": "Alpro",
            "expires": "2025-01-29",
            "days_until_expiry": 2,
            "verbrauchen_bis": "2025-01-29",
            "ablaufdatum": "2025-02-01"
          }
        ]
      }
    ],
    "last_updated": "2025-01-27T10:30:00Z",
    "timestamp": "2025-01-27T10:30:00Z"
  }
}
```

**Usage Scenarios:**

- **Use `ha-location-status`**: For quick overview and utilization statistics
- **Use `ha-location-items`**: For detailed item listings and individual location monitoring

## Security Notes

1. **Access Tokens**: The current implementation uses user access tokens which may expire. For production use, consider implementing a long-lived service token.

2. **Network Security**: Ensure your Home Assistant instance can reach your Supabase project URL.

3. **Rate Limiting**: The endpoints respect Supabase's rate limiting. Adjust scan intervals if you encounter rate limit issues.

## Troubleshooting

1. **401 Unauthorized**: Check that your access token is valid and properly formatted in the Authorization header.

2. **Empty Data**: Ensure you have items and locations in your pantry app and that the user associated with the token has access to them.

3. **Slow Updates**: Increase scan intervals in your configuration if you're hitting rate limits.

4. **Token Expiry**: Access tokens expire after some time. You may need to refresh them periodically or implement a token refresh mechanism.

## Advanced Features

For more advanced integrations, you could:

1. **MQTT Integration**: Implement real-time updates using MQTT
2. **Bidirectional Sync**: Add items to pantry from Home Assistant
3. **Shopping List Integration**: Automatically add expired items to HA shopping lists
4. **Voice Control**: Use HA's voice integration with the sensors
5. **Smart Notifications**: Use location-based or time-based smart notifications

## Support

If you encounter issues with the integration, check:

1. Home Assistant logs for REST sensor errors
2. Supabase Edge Function logs for API errors
3. Network connectivity between HA and Supabase
