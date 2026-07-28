---
description: The Dispatched record written before a worker starts; two claims, not one.
trigger: always_on
---

## The launch claim

A dispatch whose loss would matter beyond its own session gets a claim written on
the task record **before** the worker starts: a line beginning `Dispatched:`
naming who it went to, under which session, on which surface, and when. Cheap
read-only probes are exempt — nothing is lost by running one again, so claiming
for them buys graph noise instead of recoverability.

The word is the contract. A dispatch surface writes that line and a reconcile
sweep reads it by name, so a claim phrased freely is one no later pass can find.

The worker's own claim, taken from inside its session, is a separate act and is
what moves the status. The launch record exists so a worker that died before ever
claiming reads as an unanswered dispatch rather than as work nobody picked up —
and a launch claim with no worker claim behind it is exactly the stale-claim
signal a sweep probes.
