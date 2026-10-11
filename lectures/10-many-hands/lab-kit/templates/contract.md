# Contract: _the shared thing_ · v1

**Owner** _one named person_ · **Agreed by** _everyone whose code writes or reads it_ ·
**Date** _when it was agreed_
**Changing it** _how, for example: a pull request that edits this file and its examples,
reviewed by every person listed above. Code that breaks the examples does not merge._

## The rule

Write each rule so that a stranger, or an agent, could check it by reading the code or
running a test.

1. **Representation.** _Field names, type, format, unit, time zone, allowed values._
2. **Input.** _What callers send, and how it is converted on the way in._
3. **Output.** _What people see, and in which form._
4. **One place converts.** _Which module owns every conversion. Nothing else converts._
5. **Readers are strict.** _What a reader does with a value that breaks the rule. (It
   should fail loudly, never guess.)_

## Examples

Both sides of the boundary test against exactly these rows. Include at least one awkward
case (a boundary, a midnight, an empty value).

| Input | Stored and served | Shown |
|---|---|---|
| | | |
| | | |
| | | |

## Checks

- **Contract tests:** _file(s); one test for the side that writes, one for the side that
  reads, both using the examples above._
- **Integration test on the merged build:** _file._
- **CI:** _does it run on the merged result? How do you make sure a branch is tested
  against the latest `main` before it merges?_

## Not covered by this version

_What you knowingly left out, so nobody assumes it is covered._
