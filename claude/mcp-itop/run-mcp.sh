#!/bin/bash
export PYTHONPATH=/home/ondrreme/claude/mcp-itop/src
cd /home/ondrreme/claude/mcp-itop
source .env 2>/dev/null || true
exec python3 -m mcp_itop.server
