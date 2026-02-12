# WhatsApp2 Clone

A pixel-perfect clone of WhatsApp Web built with React + FastAPI + MongoDB.

## Project Structure
- **Backend**: `/app/backend/` (FastAPI + MongoDB + WebSockets)
- **Frontend**: `/app/frontend/` (React)

## Features
- JWT Authentication (Login/Register)
- Real-time messaging via WebSockets
- Contact list with last message previews and unread badges
- Message bubbles with timestamps and read receipts (double-tick)
- Typing indicators
- New chat creation
- Search contacts
- Profile pictures
- Pre-seeded test users

## Quick Login Users
| Name | Email | Password |
|------|-------|----------|
| Saswata | saswata@whatsapp2.com | password123 |
| Ananya | ananya@whatsapp2.com | password123 |
| Arjun Mehta | arjun@whatsapp2.com | password123 |
| Priya Sharma | priya@whatsapp2.com | password123 |
| Vikram Patel | vikram@whatsapp2.com | password123 |

## Tech Stack
- Frontend: React 18, Lucide Icons, CSS3
- Backend: FastAPI, Motor (MongoDB async driver), PyJWT, bcrypt
- Database: MongoDB
- Real-time: WebSockets
