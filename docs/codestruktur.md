src
├── __init__.py
├── api
│   ├── __init__.py
│   └── routes
│       ├── __init__.py
│       ├── dashboard.py
│       ├── email.py
│       ├── info.py
│       ├── integration.py
│       ├── process.py
│       └── vehicles.py
├── core
│   ├── __init__.py
│   ├── background_tasks.py
│   ├── dependencies.py
│   ├── logging_config.py
│   ├── mappings.py
│   ├── performance.py
│   └── process_config.py
├── handlers
│   ├── __init__.py
│   ├── data_transformer.py
│   ├── flowers_handler.py
│   ├── unified_handler.py
│   └── zapier_handler.py
├── main.py
├── models
│   ├── __init__.py
│   └── integration.py
└── services
    ├── __init__.py
    ├── bigquery_service.py
    ├── dashboard_service.py
    ├── email_service.py
    ├── info_service.py
    ├── process_cleanup_service.py
    ├── process_service.py
    ├── vehicle_service.py
    └── vin_decoder_service.py