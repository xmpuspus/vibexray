/** Expected business error. The model sees the message and can recover: ask the customer, try other input. */
export class ToolError extends Error {}

/** Temporary failure of an upstream system (timeout, 5xx). The executor retries these. */
export class TransientError extends Error {}
