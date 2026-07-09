#!/bin/bash
cd "$(dirname "$0")"
python3 -m uvicorn dashboard.main:app --reload
