-- Seed messages for all chats between user1 and user2–user11
-- Each chat has messages from both sides
-- The LAST message in each chat is from the OTHER user (received msg for user1)

-- user1 ↔ user2 (Ananya) — main GF chat
insert into public.chats (conversation_id, sender_id, content, created_at) values
  ('user1-user2-chat', 'user1', 'Hi , my girl . Kya haal chaal', now() - interval '5 hours 30 minutes'),
  ('user1-user2-chat', 'user2', 'Haye mera hero… Main theek hoon. Tum batao?', now() - interval '5 hours 28 minutes'),
  ('user1-user2-chat', 'user1', 'Work is important but not more important than you. Any plans for tonight?', now() - interval '5 hours 25 minutes'),
  ('user1-user2-chat', 'user2', 'Maybe late night call? Agar main saamne hoti toh kya karte?', now() - interval '5 hours 22 minutes'),
  ('user1-user2-chat', 'user1', 'Are you flirting?', now() - interval '5 hours 20 minutes'),
  ('user1-user2-chat', 'user2', 'Thoda sa flirt toh banta hai.', now() - interval '5 hours 18 minutes'),
  ('user1-user2-chat', 'user1', 'I love it, it gives me butterflies.', now() - interval '5 hours 15 minutes'),
  ('user1-user2-chat', 'user2', 'Butterflies? Main blush mode mein hoon.', now() - interval '5 hours 12 minutes'),
  ('user1-user2-chat', 'user1', 'Wanna go out tonight?', now() - interval '5 hours 10 minutes'),
  ('user1-user2-chat', 'user2', 'Always ready.', now() - interval '5 hours 8 minutes'),
  ('user1-user2-chat', 'user1', 'Should I order chocolates for you?', now() - interval '5 hours 5 minutes'),
  ('user1-user2-chat', 'user2', 'I was craving chocolates.', now() - interval '5 hours 3 minutes'),
  ('user1-user2-chat', 'user1', 'Order kar diya, gate pe aa jayega.', now() - interval '5 hours'),
  ('user1-user2-chat', 'user2', 'You are so sweet.', now() - interval '4 hours 58 minutes'),
  ('user1-user2-chat', 'user1', 'You are my spoiled girl.', now() - interval '4 hours 55 minutes'),
  ('user1-user2-chat', 'user2', 'Bas tumhari hi hoon.', now() - interval '4 hours 52 minutes'),
  ('user1-user2-chat', 'user1', 'Avinash ki party achi thi?', now() - interval '4 hours 50 minutes'),
  ('user1-user2-chat', 'user2', 'Tumhare bina boring.', now() - interval '4 hours 48 minutes'),
  ('user1-user2-chat', 'user1', 'Office busy tha, startup pressure hai.', now() - interval '4 hours 45 minutes'),
  ('user1-user2-chat', 'user2', 'Thoda time mujhe bhi invest karo.', now() - interval '4 hours 42 minutes'),
  ('user1-user2-chat', 'user1', 'Funding bhi laani hai, team lead bhi karna hai.', now() - interval '4 hours 40 minutes'),
  ('user1-user2-chat', 'user2', 'Proud of you.', now() - interval '4 hours 38 minutes'),
  ('user1-user2-chat', 'user1', 'Office competitive hai.', now() - interval '4 hours 35 minutes'),
  ('user1-user2-chat', 'user2', 'Tum shine karoge.', now() - interval '4 hours 32 minutes'),
  ('user1-user2-chat', 'user1', 'Tum possessive ho jaati ho.', now() - interval '4 hours 30 minutes'),
  ('user1-user2-chat', 'user2', 'Par main tumhari safe space hoon.', now() - interval '4 hours 28 minutes'),
  ('user1-user2-chat', 'user1', 'Thank you meri jaan.', now() - interval '4 hours 25 minutes'),
  ('user1-user2-chat', 'user2', 'Always meri jaan.', now() - interval '4 hours 22 minutes'),
  ('user1-user2-chat', 'user1', 'Lakho ladkiya marti hain mujhpe.', now() - interval '4 hours 20 minutes'),
  ('user1-user2-chat', 'user2', 'But tum mere ho.', now() - interval '4 hours 18 minutes'),
  ('user1-user2-chat', 'user1', 'Valentine plan?', now() - interval '4 hours 15 minutes'),
  ('user1-user2-chat', 'user2', 'Simple, just us.', now() - interval '4 hours 12 minutes'),
  ('user1-user2-chat', 'user1', 'Steak house booked.', now() - interval '4 hours 10 minutes'),
  ('user1-user2-chat', 'user2', 'Excited.', now() - interval '4 hours 8 minutes'),
  ('user1-user2-chat', 'user1', 'Assignment pending hai?', now() - interval '4 hours 5 minutes'),
  ('user1-user2-chat', 'user2', 'Haan.', now() - interval '4 hours 3 minutes'),
  ('user1-user2-chat', 'user1', 'Start working, baad mein baat karte hain.', now() - interval '4 hours'),
  ('user1-user2-chat', 'user2', 'Late night call pakka.', now() - interval '3 hours 58 minutes'),
  ('user1-user2-chat', 'user1', 'I love you meri jaan.', now() - interval '3 hours 55 minutes'),
  ('user1-user2-chat', 'user2', 'I love when you say jaan.', now() - interval '3 hours 52 minutes'),
  ('user1-user2-chat', 'user1', 'Haan meri jaan.', now() - interval '3 hours 50 minutes'),
  ('user1-user2-chat', 'user2', 'Dil soft ho jaata hai.', now() - interval '3 hours 48 minutes');

-- user1 ↔ user3 (Arjun Mehta)
insert into public.chats (conversation_id, sender_id, content, created_at) values
  ('user1-user3-chat', 'user1', 'Hey Arjun, are we still on for the meeting tomorrow?', now() - interval '1 day 4 hours'),
  ('user1-user3-chat', 'user3', 'Yes absolutely! I have the deck ready.', now() - interval '1 day 3 hours'),
  ('user1-user3-chat', 'user1', 'Perfect, let me know if you need anything from my side.', now() - interval '1 day 2 hours'),
  ('user1-user3-chat', 'user3', 'Will do. Also can you share the client requirements doc?', now() - interval '1 day 1 hour'),
  ('user1-user3-chat', 'user1', 'Sure, sending it now.', now() - interval '1 day 30 minutes'),
  ('user1-user3-chat', 'user3', 'See you at the meeting tomorrow!', now() - interval '1 day');

-- user1 ↔ user4 (Priya Sharma)
insert into public.chats (conversation_id, sender_id, content, created_at) values
  ('user1-user4-chat', 'user4', 'Hi! Did you get a chance to review the designs?', now() - interval '3 days 5 hours'),
  ('user1-user4-chat', 'user1', 'Yes, they look great! Just a few minor tweaks needed.', now() - interval '3 days 4 hours'),
  ('user1-user4-chat', 'user4', 'Cool, I will update them by tonight.', now() - interval '3 days 3 hours'),
  ('user1-user4-chat', 'user1', 'Sounds good. Also, I tried calling you earlier.', now() - interval '3 days 2 hours'),
  ('user1-user4-chat', 'user4', 'Oh sorry I was in a meeting. What was it about?', now() - interval '3 days 1 hour'),
  ('user1-user4-chat', 'user1', 'Just wanted to discuss the timeline. Let me know when you are free.', now() - interval '3 days 30 minutes'),
  ('user1-user4-chat', 'user4', 'I am free now, give me a call!', now() - interval '3 days');

-- user1 ↔ user5 (Vikram Patel)
insert into public.chats (conversation_id, sender_id, content, created_at) values
  ('user1-user5-chat', 'user1', 'Vikram, have you seen the new framework release?', now() - interval '4 days 6 hours'),
  ('user1-user5-chat', 'user5', 'Not yet, which one?', now() - interval '4 days 5 hours'),
  ('user1-user5-chat', 'user1', 'Next.js 15, it has some crazy improvements.', now() - interval '4 days 4 hours'),
  ('user1-user5-chat', 'user5', 'Oh nice, I will check it out tonight.', now() - interval '4 days 3 hours'),
  ('user1-user5-chat', 'user1', 'Also the new React compiler is insane.', now() - interval '4 days 2 hours'),
  ('user1-user5-chat', 'user5', 'Check out this link, really good stuff', now() - interval '4 days');

-- user1 ↔ user6 (Neha Gupta)
insert into public.chats (conversation_id, sender_id, content, created_at) values
  ('user1-user6-chat', 'user1', 'Happy birthday Neha! 🎂', now() - interval '5 days 4 hours'),
  ('user1-user6-chat', 'user6', 'Thank you so much!! 😊', now() - interval '5 days 3 hours'),
  ('user1-user6-chat', 'user1', 'Did you have a party?', now() - interval '5 days 2 hours'),
  ('user1-user6-chat', 'user6', 'Yes! It was amazing, wish you could have come.', now() - interval '5 days 1 hour'),
  ('user1-user6-chat', 'user1', 'Next time for sure! Hope you had a blast.', now() - interval '5 days 30 minutes'),
  ('user1-user6-chat', 'user6', 'Happy birthday! Hope you have a great one!', now() - interval '5 days');

-- user1 ↔ user7 (Amit Kumar)
insert into public.chats (conversation_id, sender_id, content, created_at) values
  ('user1-user7-chat', 'user7', 'Hey, can we do a quick video call?', now() - interval '6 days 5 hours'),
  ('user1-user7-chat', 'user1', 'Sure, give me 5 minutes.', now() - interval '6 days 4 hours'),
  ('user1-user7-chat', 'user7', 'No rush, ping me when ready.', now() - interval '6 days 3 hours'),
  ('user1-user7-chat', 'user1', 'Alright I am ready now.', now() - interval '6 days 2 hours'),
  ('user1-user7-chat', 'user7', 'Great, that was a productive call!', now() - interval '6 days 1 hour'),
  ('user1-user7-chat', 'user1', 'Agreed, let me document the action items.', now() - interval '6 days 30 minutes'),
  ('user1-user7-chat', 'user7', 'Sounds good, talk soon!', now() - interval '6 days');

-- user1 ↔ user8 (Rohan Singh)
insert into public.chats (conversation_id, sender_id, content, created_at) values
  ('user1-user8-chat', 'user1', 'Rohan, did you push the latest changes?', now() - interval '7 days 5 hours'),
  ('user1-user8-chat', 'user8', 'Yes, just merged to main.', now() - interval '7 days 4 hours'),
  ('user1-user8-chat', 'user1', 'Cool, I will pull and test.', now() - interval '7 days 3 hours'),
  ('user1-user8-chat', 'user8', 'Let me know if there are any issues.', now() - interval '7 days 2 hours'),
  ('user1-user8-chat', 'user1', 'Found a small bug, can you fix?', now() - interval '7 days 1 hour'),
  ('user1-user8-chat', 'user8', 'Will send the files by evening', now() - interval '7 days');

-- user1 ↔ user9 (Kavita Reddy)
insert into public.chats (conversation_id, sender_id, content, created_at) values
  ('user1-user9-chat', 'user9', 'Thanks for helping with the migration!', now() - interval '10 days 4 hours'),
  ('user1-user9-chat', 'user1', 'No problem at all, happy to help.', now() - interval '10 days 3 hours'),
  ('user1-user9-chat', 'user9', 'The data looks clean now.', now() - interval '10 days 2 hours'),
  ('user1-user9-chat', 'user1', 'Great, let me know if anything else comes up.', now() - interval '10 days 1 hour'),
  ('user1-user9-chat', 'user9', 'Thanks for the help!', now() - interval '10 days');

-- user1 ↔ user10 (Dev Team)
insert into public.chats (conversation_id, sender_id, content, created_at) values
  ('user1-user10-chat', 'user1', 'Is the v2.3 build passing CI?', now() - interval '14 days 5 hours'),
  ('user1-user10-chat', 'user10', 'Yes, all green. Deploying now.', now() - interval '14 days 4 hours'),
  ('user1-user10-chat', 'user1', 'Awesome, keep me posted.', now() - interval '14 days 3 hours'),
  ('user1-user10-chat', 'user10', 'Staging is live, running smoke tests.', now() - interval '14 days 2 hours'),
  ('user1-user10-chat', 'user1', 'Perfect, let me check staging.', now() - interval '14 days 1 hour'),
  ('user1-user10-chat', 'user10', 'Deployment is done for v2.3', now() - interval '14 days');

-- user1 ↔ user11 (Sanjay Iyer)
insert into public.chats (conversation_id, sender_id, content, created_at) values
  ('user1-user11-chat', 'user1', 'Sanjay! Long time no see.', now() - interval '16 days 5 hours'),
  ('user1-user11-chat', 'user11', 'I know right! We should catch up.', now() - interval '16 days 4 hours'),
  ('user1-user11-chat', 'user1', 'How about this weekend?', now() - interval '16 days 3 hours'),
  ('user1-user11-chat', 'user11', 'Saturday works for me.', now() - interval '16 days 2 hours'),
  ('user1-user11-chat', 'user1', 'Great, same coffee place?', now() - interval '16 days 1 hour'),
  ('user1-user11-chat', 'user11', 'Let''s catch up this weekend', now() - interval '16 days');
