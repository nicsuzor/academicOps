---
title: Telegram Reply Button Layout and Predefined Row
status: ready
---

# Telegram Reply Button Layout and Predefined Row

This specification defines the button layout customization and predefined button consolidation contracts for reply messages in the `ida-telegram` plugin. It serves operators interacting with conversational agents over Telegram who need compact, multi-row button grids and a single prominent header row for system actions.

## User stories

### US-1 Caller-Specified Button Layout Grid

As an operator interacting with multi-option prompts (such as skill or workflow selection checklists), I want reply buttons arranged in multi-column rows rather than an unwieldy single vertical column, so that option choices fit comfortably on a mobile screen without excessive scrolling.

- **AC-1.1** Given a reply request carrying 8 option buttons arranged in a multi-row grid (via a 2D button array or layout specifications), when the message is sent, then the Telegram inline keyboard contains the buttons arranged in the caller's chosen multi-row grid rather than one button per row.
- **AC-1.2** Given a flat array of buttons with a `button_layout` array (e.g. `[3, 3, 2]`), when the message is sent, then the Telegram inline keyboard groups buttons into rows according to the specified count per row.
- **AC-1.3** Given a flat array of buttons with `buttons_per_row` (or numeric `button_layout`), when the message is sent, then the Telegram inline keyboard partitions buttons into rows of that size.
- **AC-1.4** Given a flat array of buttons without layout options, when the message is sent, then the plugin preserves backward compatibility by placing one button per row.

### US-2 Predefined Buttons Consolidated on the Default First Row

As an operator reading agent replies with system actions (such as Details, Check logic, and Explain), I want all active predefined buttons grouped together on a single default row at the top above custom option buttons, so that common navigational and meta-actions remain predictable and compact without consuming multiple rows.

- **AC-2.1** Given `predefined_row: true` with `detailsId` present and message actions disabled (`actions: false`), when the reply is sent, then `🔍 Details` is placed on the first row (row 0).
- **AC-2.2** Given `predefined_row: true` with `detailsId` present and message actions enabled (`actions: true`), when the reply is sent, then `🔍 Details`, `🧐 Check logic`, and `💡 Explain` all sit together on the same first row (row 0).
- **AC-2.3** Given `predefined_row: true` with both predefined buttons and caller buttons present, when the reply is sent, then the consolidated predefined row sits at the top (row 0) above the caller's custom button rows.
- **AC-2.4** Given `predefined_row: false` or omitted, when the reply is sent, then predefined buttons maintain their legacy multi-row arrangement below caller buttons.

## Design

### 1. Custom Button Layouts (US-1)

1. **Input Flexibility:**
   The `reply` tool accepts buttons in either of two structures:
   - **2D Grid Array (`buttons: ReplyButtonOption[][]`):** The caller directly defines each row as an array of button objects.
   - **Flat Array (`buttons: ReplyButtonOption[]`):** Sliced into rows using layout parameters:
     - `button_layout: number[]` specifies the explicit button count for each successive row (e.g. `[3, 3, 2]`). Any remaining buttons are placed in subsequent rows following the last specified count or 1.
     - `buttons_per_row: number` (or numeric `button_layout: number`) partitions the flat array into uniform rows of that maximum width.
     - `row: number` property on individual button objects allows sparse or explicit row grouping.
   - **Default Behavior:** A flat button array without layout parameters defaults to 1 button per row for backward compatibility.

2. **Verification Check:**
   - Checked by `plugins/ida-telegram/test/reply-buttons.test.ts` (AC1 tests: 2D array grid, `button_layout: [3, 3, 2]`, `buttons_per_row: 4`, and default single-column fallback).

### 2. Predefined Row Consolidation (US-2)

1. **Option Activation:**
   Setting `predefined_row: true` (or `predefined_buttons_row: true`) on `reply` activates single-row consolidation for all active predefined buttons.

2. **Layout Order and Placement:**
   - **Placement:** The consolidated predefined row is placed at row index 0 (the top-most row of the inline keyboard), above any caller option buttons.
   - **Composition:** Gathers all active predefined buttons onto that single row:
     1. `🔍 Details` (when `detailsId` is present)
     2. `🔍 Review diff` (when `review` is present)
     3. Feedback buttons (`👍`, `👎`, when `feedback: true`)
     4. Message action buttons (`🧐 Check logic`, `💡 Explain`, when `actions !== false`)
   - **Zero Predefined Buttons:** When no predefined buttons are active (e.g. `actions: false` without details or feedback), no empty row is prepended.

3. **In-Place Action Interaction:**
   When an operator taps `🧐 Check logic` or `💡 Explain`, the callback handler filters out the tapped actions while preserving other buttons on that same row (such as `🔍 Details`) and all caller rows below.

4. **Verification Check:**
   - Checked by `plugins/ida-telegram/test/reply-buttons.test.ts` (AC2 tests: Details alone, Details with Check logic and Explain on row 0, predefined row above caller grid rows, and legacy layout preservation when option is unset).
