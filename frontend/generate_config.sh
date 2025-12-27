#!/bin/bash
echo "window.config = { API_URL: \"$API_URL\" };" > public/config.js
echo "Generated public/config.js with API_URL: $API_URL"
