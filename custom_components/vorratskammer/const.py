DOMAIN = "vorratskammer"

CONF_SUPABASE_URL = "supabase_url"        # e.g., https://bscdbvbvylwqhkijhnub.supabase.co
CONF_EMAIL = "email"
CONF_PASSWORD = "password"

CONF_DAYS_AHEAD = "days_ahead"            # for ha-expiring-items
CONF_SCAN_SUMMARY = "scan_summary"
CONF_SCAN_EXPIRING = "scan_expiring"
CONF_SCAN_LOCATIONS = "scan_locations"

DEFAULT_DAYS_AHEAD = 7
DEFAULT_SCAN_SUMMARY = 300
DEFAULT_SCAN_EXPIRING = 600
DEFAULT_SCAN_LOCATIONS = 300

STORAGE_TOKENS = "tokens"  # key in hass.data[DOMAIN][entry_id]
