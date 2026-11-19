---
title: Telegram Question Card Delivery Guarantee
status: ready
---

# Telegram Question Card Delivery Guarantee

This specification defines the delivery guarantee for structured questions posted to the operator over Telegram. It guarantees that every question reported as posted to the operator was confirmed delivered to the chat interface with its selectable option buttons, and that delivery or infrastructure failures halt and surface immediately rather than leaving agents waiting indefinitely for answers to undelivered questions.

## User stories

### US-1 Confirmed Delivery Verification and Button Rendering

As an operator interacting with an agent over Telegram, I want every question reported posted by the agent to appear in my chat with its selectable option buttons, so that I can make decisions and reply directly in the client.

- **AC-1.1** Given a question with chat delivery enabled, when the question is dispatched to the Telegram interface, then the message is delivered carrying formatted text and vertical option buttons, receives confirmed delivery with a message identifier, records the identifier on the question record, and only then reports the question as posted.
- **AC-1.2** Given the question bridge starts up, when a question is received from an asking agent, then the live communication client reference is resolved dynamically and dispatches the card without dropping questions due to lifecycle ordering.
- **AC-1.3** Given the messaging API rejects rich formatting entities on a question card, when delivery is attempted, then the card is resent as unformatted text with all option buttons preserved.

### US-2 Loud Failure Surfacing on Delivery and Infrastructure Errors

As an autonomous agent asking a user question over Telegram, I want infrastructure and delivery failures to halt loudly and surface immediately, so that I am never told a question was posted when it was not delivered and never end my turn waiting for an impossible answer.

- **AC-2.1** Given a question with chat delivery requested, when the communication client is not running, the target chat identifier is missing, or the messaging API fails, then the tool returns an error result with error signaling enabled rather than reporting that the question was posted.
- **AC-2.2** Given the asking tool's execution hook is invoked in a primary Telegram environment, when the transport socket is missing, the connection fails, or a delivery error is received, then the hook writes the failure description to standard error and halts execution with a non-zero exit code rather than claiming successful delivery or falling back silently.

## Design

### 1. Dynamic Client Resolution

The question transport resolves the live communication client dynamically at message dispatch time rather than capturing a static reference during startup. This ensures that lifecycle ordering differences between server initialization and client readiness never drop question cards or cause false-positive acknowledgments.

### 2. Confirmed Send Contract

Before returning success to an asking agent:

1. For questions routed to the chat interface:
   - Validate that the messaging client is active and a target chat identifier is configured;
   - Render the formatted question card and its option buttons;
   - Dispatch the question to the messaging API;
   - Confirm receipt of a successful response containing a valid message identifier;
   - Record the message identifier on the question record;
   - If delivery fails at any step, return an explicit error payload and do not claim delivery.
2. Only return success if the question was either confirmed delivered to the chat interface or explicitly designated for web interface delivery only.

### 3. Fail-Fast Execution on Transport Failure

When the question execution hook operates in a designated primary Telegram environment:

1. If the transport socket does not exist or connection fails, the hook writes the failure to standard error and halts execution with exit code 1.
2. If the response indicates delivery failure or unparseable output, the hook writes the failure to standard error and halts execution with exit code 1.
3. The hook emits a blocking denial payload confirming delivery only when the question transport explicitly confirms delivery with a valid question identifier. Silent fallback branches to standard terminal prompts are prohibited when operating in a primary Telegram environment.
