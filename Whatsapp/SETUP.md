# WhatsApp Chat Setup with User Authentication

## Database Setup

You need to run the SQL commands in your Supabase dashboard to set up the database tables.

### Steps:

1. Go to your Supabase dashboard: https://app.supabase.com/project/bysyalujziclkdjmjggn
2. Click on "SQL Editor" in the left sidebar
3. Click "New Query"
4. Copy and paste the contents of `supabase.sql`
5. Click "Run" to execute the SQL

This will create:
- `profiles` table: stores user information (username, email)
- `chats` table: stores chat messages with proper foreign key to profiles
- Row Level Security (RLS) policies: ensures users can only send messages as themselves

## Important Changes

### What's New:
- **User Authentication**: Users must sign up/login before chatting
- **User Profiles**: Each user has a unique username and email
- **Secure Messaging**: Messages are tied to authenticated user IDs
- **Multi-User Support**: Multiple users can chat in the same conversation

### Database Changes:
- `chats.sender_id` is now a UUID (foreign key to `profiles.id`) instead of text
- Added `profiles` table for user information
- Added proper RLS policies for security

## Testing with Two Browsers

1. Open the app in two different browsers (e.g., Chrome and Firefox)
2. In Browser 1:
   - Sign up with email: `user1@example.com` and password
   - Set username: `User One`
3. In Browser 2:
   - Sign up with email: `user2@example.com` and password
   - Set username: `User Two`
4. Both users can now chat in real-time!

## Features

✅ User Registration & Login
✅ Secure Authentication with Supabase Auth
✅ Real-time messaging
✅ Multi-user support
✅ User profiles with usernames
✅ Sign out functionality

## Notes

- The sign-out button is the menu icon (three dots) in the top right of the contacts panel
- Your username/email is displayed when you hover over your profile picture
- Messages sent by you appear on the right (green), messages from others appear on the left (white)
