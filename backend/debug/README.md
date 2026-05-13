# Debug Scripts

This folder contains debug and diagnostic scripts for troubleshooting the application.

## Files

- `debug_dashboard.py` - Check what's in the database and clear stale cache
- `debug_exact.py` - Exact dashboard simulation with correct workspace
- `debug_workspace.py` - Check workspace_id alignment
- `debug_monte_carlo.py` - Debug Monte Carlo simulation functionality

## Usage

Run these scripts directly with Python when you need to debug specific issues:

```bash
python backend/debug/debug_dashboard.py
python backend/debug/debug_exact.py
python backend/debug/debug_workspace.py
python backend/debug/debug_monte_carlo.py
```

These scripts are for development and debugging purposes only and should not be used in production.
