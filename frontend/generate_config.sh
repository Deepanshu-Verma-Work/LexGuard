#!/bin/bash
# Generate config.js for the frontend, ensuring the path is correct from the repo root
echo "window.config = { API_URL: \"$API_URL\" };" > frontend/public/config.js
