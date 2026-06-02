#!/bin/bash
set -e
echo "Starting Bottle Signature Frontend v1.5.7"
cd "$(dirname "$0")/frontend"
npm install
npm start
