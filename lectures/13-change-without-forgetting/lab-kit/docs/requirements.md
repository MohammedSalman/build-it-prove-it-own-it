# AfterHours tickets: requirements

The festival runs on **Friday 9, Saturday 10 and Sunday 11 October 2026**. All times are
festival local time. A festival day runs from 00:00:00 up to, but not including,
00:00:00 the next day.

Events and reservations are unchanged from Week 1: confirmed reservations for an event
never exceed its capacity.

## Day tickets (v1 and v2)

**T1 · Days.** A day ticket is for one festival day. Selling a ticket for any other date
is refused.

**T2 · The gate.** A day ticket admits its holder on its day, at any time during that
day. On any other day the gate refuses it and says which day it is for.

**T3 · Changing day.** A holder can move a day ticket to another festival day while
both days are still ahead: before 00:00:00 on the ticket's current day, and before
00:00:00 on the new day. Once either day has begun, the ticket can't move.

> Example: at 12:00 on Thursday 8 October, a Friday ticket can move to Saturday. At
> 18:00 on Friday 9 October it can't: its own day has begun.

**T4 · Codes.** Every ticket has a code, printed on the wristband and scanned at the
gate. Codes are unique. (Nothing else about the code is specified.)

## Festival passes (new in v2)

**T5 · Passes.** A festival pass covers two or three consecutive festival days, from
its first day to its last day inclusive (Friday–Saturday, Saturday–Sunday or
Friday–Sunday). It admits its holder on each of those days, as in T2. A pass can't
change days.

**T6 · Passes need v2 everywhere.** Passes go on sale only when no v1 server is left: v1
knows only single days and would turn a pass holder away after the first day.

## The migration's promise

**M1 · Nothing forgotten.** Every ticket that exists before the migration, and every
ticket sold or moved during it by v1 or by v2, admits the same holder on exactly the
same days after the migration. (Checked by comparing meaning: see
`migrations/meaning.py`.)

**M2 · No stop.** Selling, moving and scanning tickets keep working throughout: the
gates are open all weekend.
