#!/bin/bash

# Script to run WhatsApp on port 3000 and BlinkIt server on port 3001

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to handle cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down servers...${NC}"
    kill $WHATSAPP_PID $BLINKIT_PID 2>/dev/null
    exit
}

# Set up trap to catch Ctrl+C
trap cleanup SIGINT SIGTERM

echo -e "${GREEN}Starting applications...${NC}"
echo -e "${BLUE}WhatsApp will run on http://localhost:3000${NC}"
echo -e "${BLUE}BlinkIt server will run on http://localhost:3001${NC}"
echo ""

# Start WhatsApp Next.js app on port 3000
if [ ! -d "Whatsapp" ]; then
    echo -e "${YELLOW}Error: Whatsapp folder not found!${NC}"
    exit 1
fi

cd Whatsapp || exit 1
PORT=3000 npm run dev &
WHATSAPP_PID=$!
cd ..

# Start BlinkIt server on port 3001
if [ ! -d "BlinkIt/server" ]; then
    echo -e "${YELLOW}Error: BlinkIt/server folder not found!${NC}"
    kill $WHATSAPP_PID 2>/dev/null
    exit 1
fi

cd BlinkIt/server || exit 1
PORT=3001 npm run dev &
BLINKIT_PID=$!
cd ../..

echo -e "${GREEN}Both applications are running!${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop both servers${NC}"

# Wait for both processes
wait $WHATSAPP_PID $BLINKIT_PID
