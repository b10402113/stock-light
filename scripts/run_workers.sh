#!/bin/bash
# Start all ARQ workers for StockLight

set -e

# Activate virtual environment
source .venv/bin/activate

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Trap to kill all background processes on exit
trap 'kill $(jobs -p) 2>/dev/null; echo -e "${YELLOW}All workers stopped.${NC}"' EXIT

echo -e "${GREEN}Starting ARQ Workers for StockLight...${NC}"
echo ""

# Start Default Worker (system tasks and scheduling)
echo -e "${YELLOW}[1] Starting DefaultWorker (system tasks, cron jobs)...${NC}"
arq src.tasks.worker.DefaultWorkerSettings &
PID_DEFAULT=$!
echo -e "   PID: $PID_DEFAULT"

# Start API Worker (batch processing, rate-limited)
echo -e "${YELLOW}[2] Starting ApiWorker (API batch processing)...${NC}"
arq src.tasks.worker.ApiWorkerSettings &
PID_API=$!
echo -e "   PID: $PID_API"

echo ""
echo -e "${GREEN}All workers started successfully!${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all workers.${NC}"
echo ""

# Wait for all background processes
wait