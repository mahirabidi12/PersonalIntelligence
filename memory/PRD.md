# Blinkit2 & WhatsApp2 - Product Requirements Document

## Original Problem Statements
1. **WhatsApp2**: Build a WhatsApp Web clone with real-time messaging, contacts sidebar, chat conversations, JWT auth, WebSocket messaging
2. **Blinkit2**: Build a Blinkit clone (Indian grocery delivery app) in a new folder with name Blinkit2, with data and everything

## Architecture
- **Frontend**: React 18 (CRA) on port 3000
- **Backend**: FastAPI on port 8001
- **Database**: MongoDB (local)
- **Auth**: JWT (PyJWT + bcrypt)

## Current Active App: Blinkit2

### Core Features Implemented (Jan 2026)
- [x] Home page with yellow banner, 12 category grid, product carousels
- [x] 64+ Indian grocery products with realistic names, prices in INR, images
- [x] Product browsing by category with horizontal scroll
- [x] Search products (text search)
- [x] Product detail page with description, pricing, add to cart
- [x] Cart sidebar with add/remove/update quantity
- [x] Bill details (items total, delivery charge, grand total)
- [x] Checkout with address form + Cash on Delivery
- [x] Order placement with "BK2-" order IDs
- [x] Order history page
- [x] JWT authentication (login/register)
- [x] Quick login with demo user
- [x] "Delivery in 10 minutes" branding throughout
- [x] Blinkit yellow-green theme (#F8CB46 + #0C831F)
- [x] Discount badges, strikethrough prices
- [x] Responsive design

### Categories (12)
Fruits & Vegetables, Dairy & Bread, Snacks & Munchies, Cold Drinks & Juices, Instant & Frozen Food, Tea Coffee & Health Drinks, Atta Rice & Dal, Masala Oil & More, Sweet Tooth, Baby Care, Cleaning Essentials, Personal Care

### Test Results
- Backend: 100% (15/15 tests passed)
- Frontend: 100% (25/25 features verified)

## Previous App: WhatsApp2
- Real-time messaging via WebSockets
- JWT auth, contact sidebar, chat bubbles, read receipts
- All tests passed (100%)
- Files preserved in `/app/whatsApp2/`

## Prioritized Backlog
### P0 (Critical) - None remaining for MVP

### P1 (High)
- Product image upload/management
- Multiple delivery addresses
- Order tracking with live status updates
- Online payment integration (Razorpay/Stripe)

### P2 (Medium)
- Coupon codes & offers
- Product reviews & ratings
- Wishlist/saved items
- Push notifications for order updates
- Admin panel for product/order management

### P3 (Low)
- Dark mode
- Multi-language support (Hindi, etc.)
- Referral system
- Delivery partner tracking on map
