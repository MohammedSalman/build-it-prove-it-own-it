# AfterHours: what we promised

An excerpt from the team's scope agreement (Week 2), signed off by the product lead.
**Tests come from this page, not from the code.** When the code and this page disagree,
this page wins until the team agrees to change it, and a change to it is a decision with a
name and a date, not a quiet edit.

All times are festival local time.

### R1 · Capacity
Confirmed reservations for an event never exceed its capacity.

### R2 · Places left
The programme shows **places left = capacity − confirmed reservations**, at every moment.

### R3 · Cancelling
A confirmed reservation can be cancelled, and its place becomes free for someone else.
Cancelling a reservation that is already cancelled changes nothing: the answer is 200 and
every count stays the same. Cancelling a reservation that does not exist answers 404.

### R4 · The door check-in window
Check-in opens 30 minutes before the event starts and closes when the event ends.
The opening time is **inside** the window. The end time is **not**: at the exact end time,
check-in is closed.

For an event from 20:00 to 22:00, the window runs from 19:30:00 up to, but not including,
22:00:00.

### R5 · Who can check in
Only a confirmed reservation can be checked in, and only once. A cancelled reservation is
refused. A second check-in is refused, and the first check-in time is kept.

### R6 · No payment for a full event
Someone who asks for a place at an event that is already full is turned away before any
payment is authorised. (When two people race for the last place, the loser's authorisation
is released later: Week 6.)
