-- Profiles table for user information (no auth dependency)
create table public.profiles (
  id text primary key,
  username text unique not null,
  email text not null,
  created_at timestamptz not null default timezone('utc', now())
);

-- Disable RLS so mock users can read/write freely
alter table public.profiles enable row level security;

create policy "Allow all on profiles"
on public.profiles
for all
using (true)
with check (true);

-- Chats table for WhatsApp-style chat
create table public.chats (
  id uuid primary key default gen_random_uuid(),
  conversation_id text not null,
  sender_id text not null references public.profiles(id) on delete cascade,
  content text not null,
  created_at timestamptz not null default timezone('utc', now())
);

alter table public.chats enable row level security;

create policy "Allow all on chats"
on public.chats
for all
using (true)
with check (true);

-- Seed all users
insert into public.profiles (id, username, email) values
  ('user1', 'User 1', 'user1@mock.local'),
  ('user2', 'Ananya', 'user2@mock.local'),
  ('user3', 'Arjun Mehta', 'user3@mock.local'),
  ('user4', 'Priya Sharma', 'user4@mock.local'),
  ('user5', 'Vikram Patel', 'user5@mock.local'),
  ('user6', 'Neha Gupta', 'user6@mock.local'),
  ('user7', 'Amit Kumar', 'user7@mock.local'),
  ('user8', 'Rohan Singh', 'user8@mock.local'),
  ('user9', 'Kavita Reddy', 'user9@mock.local'),
  ('user10', 'Dev Team', 'user10@mock.local'),
  ('user11', 'Sanjay Iyer', 'user11@mock.local')
on conflict (id) do nothing;
