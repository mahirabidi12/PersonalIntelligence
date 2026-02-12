# WhatsApp2 - Product Requirements Document

## Original Problem Statement
Build a WhatsApp clone called "whatsApp2" - a pixel-perfect clone of WhatsApp Web with real-time messaging, UI and backend.

## Architecture
- **Frontend**: React 18 (CRA) on port 3000
- **Backend**: FastAPI on port 8001
- **Database**: MongoDB (local)
- **Real-time**: WebSockets (native)
- **Auth**: JWT (PyJWT + bcrypt)

## User Personas
- **Primary**: Users wanting a WhatsApp-like messaging experience
- **Secondary**: Developers learning full-stack real-time app development

## Core Requirements (Static)
1. JWT-based authentication (email + password)
2. Real-time 1-on-1 messaging via WebSockets
3. Contact list sidebar with search, last message preview, unread badges
4. Message bubbles (sent=green, received=white) with timestamps
5. Double-tick read receipts (gray=sent, blue=read)
6. Typing indicators
7. New chat creation
8. Profile pictures
9. Pre-seeded test data (11 users, conversations)

## What's Been Implemented (Jan 2026)
- [x] Login/Register page with quick login
- [x] Main chat interface (sidebar + chat panel)
- [x] Real-time messaging via WebSockets
- [x] Message read receipts (double-tick)
- [x] Typing indicators
- [x] Contact search
- [x] New chat creation
- [x] Unread message badges
- [x] Logout functionality
- [x] Chat background pattern (WhatsApp-style)
- [x] Responsive layout

## Prioritized Backlog
### P0 (Critical)
- None remaining for MVP

### P1 (High)
- Group chat UI (backend ready)
- Media/file sharing
- Message delete/edit

### P2 (Medium)
- Voice/Video call UI
- Status/Stories
- Emoji picker
- Message forwarding/reply
- User profile editing

### P3 (Low)
- Dark mode toggle
- Message search within chat
- Notification sounds
- AI smart replies

## Files Structure
```
/app/backend/server.py       - FastAPI backend (auth, chat, WebSocket)
/app/backend/.env            - Backend environment variables
/app/frontend/src/App.js     - Main React component
/app/frontend/src/App.css    - All styles
/app/frontend/src/components/
  - LoginPage.js             - Auth page
  - Sidebar.js               - Contact list sidebar
  - ChatPanel.js             - Message view + input
  - EmptyChat.js             - Default empty state
```
