# Telegram Bot Improvement Plan

This document outlines the step-by-step plan to improve the bot's reliability, performance, and correctness based on the recent code review.

## Phase 1: Critical Fixes (Correctness & API Requirements)

### 1. Fix Syntax Error in Payment Handler
**Issue:** The `successful_payment` event handler uses `await` but is not declared as an `async` function, which causes a fatal `SyntaxError`.
**Action:** Change `bot.on('successful_payment', (ctx) => { ... })` to `bot.on('successful_payment', async (ctx) => { ... })`.

### 2. Implement `pre_checkout_query` Handler
**Issue:** Telegram requires bots to acknowledge `pre_checkout_query` within 10 seconds, or the payment is aborted.
**Action:** Add a listener for `pre_checkout_query` that calls `await ctx.answerPreCheckoutQuery(true)` before the `successful_payment` event occurs.

### 3. Add Resilient Error Handling for Payment Fulfillment
**Issue:** If the database operation to activate premium fails *after* a successful charge, it throws an unhandled rejection, leaving the user without their premium status and no feedback.
**Action:** Wrap the `activatePremium` call inside a `try/catch` block within the `successful_payment` handler. Log the error for admin reconciliation and notify the user to contact support if it fails.

## Phase 2: Performance & Best Practices

### 4. Optimize Database Queries with Concurrent Execution
**Issue:** The `checkUsage` function awaits `getUsage` and `checkPremium` sequentially, unnecessarily doubling the latency.
**Action:** Refactor the function to use `Promise.all` so both database queries execute concurrently.

### 5. Enforce `await` on Telegraf Context Methods
**Issue:** Failing to `await` middleware actions like `ctx.reply` or `ctx.replyWithInvoice` breaks Telegraf's error handling chain and can cause silent failures on rate limits.
**Action:** Review command and action handlers, ensuring all `ctx.*` methods that return Promises are properly `await`ed.

## Phase 3: Security and Maintenance Agent

### 6. Implement Security and Cleanup Agent
**Issue:** The project lacks a dedicated agent for security and maintenance tasks.
**Action:** Plan to implement a security and cleanup agent using an OpenCode instance. This agent will be responsible for general security checks, code cleanliness, and maintenance tasks.

**Reference:** [OpenCode Agents Documentation](https://opencode.ai/docs/agents/)

## Notes
- The security and cleanup agent implementation is planned for a future phase and will be addressed after the critical fixes and performance improvements are completed.
