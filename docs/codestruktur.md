thomas@WS-IT-001:~/dev/ra-autohaus-tracker$ tree src scripts
src
├── __init__.py
├── __pycache__
│   ├── __init__.cpython-312.pyc
│   └── main.cpython-312.pyc
├── api
│   ├── __init__.py
│   ├── __pycache__
│   │   └── __init__.cpython-312.pyc
│   └── routes
│       ├── __init__.py
│       ├── __pycache__
│       │   ├── __init__.cpython-312.pyc
│       │   ├── dashboard.cpython-312.pyc
│       │   ├── email.cpython-312.pyc
│       │   ├── info.cpython-312.pyc
│       │   ├── integration.cpython-312.pyc
│       │   ├── process.cpython-312.pyc
│       │   └── vehicles.cpython-312.pyc
│       ├── dashboard.py
│       ├── email.py
│       ├── info.py
│       ├── integration.py
│       ├── process.py
│       └── vehicles.py
├── core
│   ├── __init__.py
│   ├── __pycache__
│   │   ├── __init__.cpython-312.pyc
│   │   └── dependencies.cpython-312.pyc
│   └── dependencies.py
├── handlers
│   ├── __init__.py
│   ├── __pycache__
│   │   ├── __init__.cpython-312.pyc
│   │   ├── data_transformer.cpython-312.pyc
│   │   ├── flowers_handler.cpython-312.pyc
│   │   ├── unified_handler.cpython-312.pyc
│   │   └── zapier_handler.cpython-312.pyc
│   ├── data_transformer.py
│   ├── flowers_handler.py
│   ├── unified_handler.py
│   └── zapier_handler.py
├── main.py
├── models
│   ├── __init__.py
│   ├── __pycache__
│   │   ├── __init__.cpython-312.pyc
│   │   └── integration.cpython-312.pyc
│   └── integration.py
└── services
    ├── __init__.py
    ├── __pycache__
    │   ├── __init__.cpython-312.pyc
    │   ├── bigquery_service.cpython-312.pyc
    │   ├── dashboard_service.cpython-312.pyc
    │   ├── email_service.cpython-312.pyc
    │   ├── info_service.cpython-312.pyc
    │   ├── process_cleanup_service.cpython-312.pyc
    │   ├── process_service.cpython-312.pyc
    │   └── vehicle_service.cpython-312.pyc
    ├── bigquery_service.py
    ├── dashboard_service.py
    ├── email_service.py
    ├── info_service.py
    ├── process_cleanup_service.py
    ├── process_service.py
    └── vehicle_service.py
scripts
├── bashrc_additions.sh
├── build-and-push.sh
├── deploy
├── deploy-all.sh
├── deploy-cloud-run.sh
├── manage-secrets.sh
├── ra-db.sh
├── ra-env.sh
├── ra-monitor.sh
├── ra-test.sh
├── ra-test.sh.bak
├── server-control.sh
├── setup
│   ├── __pycache__
│   │   ├── bigquery_views.cpython-312.pyc
│   │   └── setup_bigquery.cpython-312.pyc
│   ├── bigquery_tables.py
│   ├── bigquery_views.py
│   ├── create_views.py
│   └── setup_bigquery.py
├── setup-dev.sh
├── setup-env.sh
├── sql
│   ├── db_status.sql
│   ├── processes_active.sql
│   ├── processes_list.sql
│   └── vehicles_list.sql
├── start-dev.sh
├── test
│   ├── test_bigquery_intagration.sh
│   ├── test_update.py
│   └── verify_bigquery.py
├── test-email-credentials.py
└── test_credentials.py

20 directories, 83 files
thomas@WS-IT-001:~/dev/ra-autohaus-tracker$