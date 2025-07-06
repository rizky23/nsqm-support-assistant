# config/api_config.py

# Telkomsel API Configuration
TELKOMSEL_API = {
    "app_key": "d23cd17c-b89e-4e88-ac46-3fe0b35e6314",
    "app_secret": "c6ce9adb3a026ee61aa05681359cb2c5",
    "token_url": "https://10.77.128.111:38443/apigovernance/tokens/aksk",
    "query_url": "https://10.77.128.112:28701/apiaccess/cccommon/v1/query/queryHistoryInfo",
    "timeout": 30,
    "max_retries": 2,
    "token_expiry_hours": 1,
    "token_refresh_buffer_minutes": 5
}

# API Request Defaults
DEFAULT_QUERY_PARAMS = {
    "sceneComb": 1002,
    "roamComb": 1,
    "uuid": "FEKAKFMOJOZgFA7iNzKQJGMQ9JLZJ7mi",
    "templateCode": "CCH",
    "language": "en_US",
    "userName": "admin",
    "granularity": "1h",
    "serviceid": "10010"
}

# Response field mappings
API_FIELD_MAPPINGS = {
    "TOTALTRAFFIC": {
        "name": "Total Traffic",
        "unit": "MB",
        "description": "Total data usage"
    },
    "TOTALSCORE": {
        "name": "Total Score", 
        "unit": "",
        "description": "Quality score (0-100)"
    },
    "TOTALINTERNALLATENCYCCH": {
        "name": "Latency",
        "unit": "ms", 
        "description": "Network latency"
    },
    "UTC": {
        "name": "Timestamp",
        "unit": "unix",
        "description": "Unix timestamp"
    },
    "TEXT": {
        "name": "Time",
        "unit": "datetime",
        "description": "Human readable time"
    }
}

# Error code mappings
API_ERROR_CODES = {
    400: "Bad Request - Invalid parameters",
    401: "Unauthorized - Token expired or invalid",
    403: "Forbidden - Access denied",
    404: "Not Found - MSISDN or data not found",
    429: "Too Many Requests - Rate limit exceeded",
    500: "Internal Server Error - API server error",
    502: "Bad Gateway - API server unavailable",
    503: "Service Unavailable - API maintenance",
    504: "Gateway Timeout - API response timeout"
}

# Chart.js Configuration
CHART_CONFIG = {
    "cdn_url": "https://cdn.jsdelivr.net/npm/chart.js",
    "default_colors": {
        "traffic": {"border": "rgb(54, 162, 235)", "background": "rgba(54, 162, 235, 0.2)"},
        "score": {"border": "rgb(255, 99, 132)", "background": "rgba(255, 99, 132, 0.2)"},
        "latency": {"border": "rgb(75, 192, 192)", "background": "rgba(75, 192, 192, 0.2)"}
    },
    "chart_height": 400,
    "animation_duration": 1000
}

# MSISDN Validation
MSISDN_CONFIG = {
    "indonesian_country_code": "62",
    "valid_prefixes": [
        "811", "812", "813", "821", "822", "823", "851", "852", "853",  # Telkomsel
        "814", "815", "816", "855", "856", "857", "858",                 # Indosat
        "817", "818", "819", "859", "877", "878",                        # XL
        "838", "831", "832", "833",                                      # Axis
        "895", "896", "897", "898", "899"                                # Three
    ],
    "telkomsel_prefixes": ["811", "812", "813", "821", "822", "823", "851", "852", "853"],
    "min_length": 10,
    "max_length": 15
}

# Time parsing configuration
TIME_CONFIG = {
    "max_days_ago": 30,
    "default_time_ranges": {
        "morning": {"start": "06:00", "end": "11:59"},
        "afternoon": {"start": "12:00", "end": "17:59"},
        "evening": {"start": "18:00", "end": "22:59"},
        "night": {"start": "23:00", "end": "05:59"}
    },
    "time_window_minutes": 30  # Default window for specific time queries
}

# Response templates
RESPONSE_TEMPLATES = {
    "no_data": "📱 **Data untuk nomor {msisdn}**\n\n❌ Tidak ada data ditemukan untuk periode {period}.",
    "api_error": "❌ **Gagal mengambil data:** {error}",
    "invalid_msisdn": "❌ **Nomor tidak valid:** {msisdn} bukan format MSISDN Indonesia.",
    "non_telkomsel": "❌ **Nomor {msisdn} bukan nomor Telkomsel.** Sistem hanya mendukung analisis nomor Telkomsel.",
    "success_basic": "✅ **Data berhasil diambil untuk {msisdn}**\n\nPeriode: {period}\nTotal Traffic: {traffic}\nAverage Score: {score}",
}

# Cache configuration
CACHE_CONFIG = {
    "enabled": True,
    "ttl_minutes": 10,  # Cache for 10 minutes
    "max_entries": 100,
    "key_format": "smartcare_{msisdn}_{start_time}_{end_time}"
}

# Logging configuration
LOGGING_CONFIG = {
    "log_api_requests": True,
    "log_response_size": True,
    "log_execution_time": True,
    "max_log_response_length": 500
}