import { Injectable } from '@nestjs/common';
import type { ChatCompletionTool } from 'openai/resources/chat/completions';

/**
 * Typed, executable tools the agent can call. Definitions are advertised to the
 * model; `execute()` runs the one the model picks. Replace the mock bodies with
 * real integrations (DB, orders service, helpdesk API, ...).
 */
@Injectable()
export class ToolsService {
  readonly definitions: ChatCompletionTool[] = [
    {
      type: 'function',
      function: {
        name: 'get_order_status',
        description: 'Look up the current status of a customer order by its ID.',
        parameters: {
          type: 'object',
          properties: {
            orderId: { type: 'string', description: 'The order ID, e.g. "ORD-1234".' },
          },
          required: ['orderId'],
        },
      },
    },
    {
      type: 'function',
      function: {
        name: 'create_support_ticket',
        description: 'Create a support ticket when an issue needs a human follow-up.',
        parameters: {
          type: 'object',
          properties: {
            email: { type: 'string', description: 'Customer email address.' },
            summary: { type: 'string', description: 'Short summary of the issue.' },
          },
          required: ['email', 'summary'],
        },
      },
    },
  ];

  async execute(name: string, args: Record<string, unknown>): Promise<string> {
    switch (name) {
      case 'get_order_status': {
        const orderId = String(args.orderId ?? '');
        // TODO: replace with a real lookup against your orders service / DB.
        return JSON.stringify({ orderId, status: 'shipped', eta: '2 business days' });
      }
      case 'create_support_ticket': {
        const ticketId = 'TCK-' + Math.floor(100000 + Math.random() * 900000);
        // TODO: persist the ticket / call your helpdesk API.
        return JSON.stringify({ ticketId, email: args.email ?? null, status: 'open' });
      }
      default:
        return JSON.stringify({ error: `Unknown tool: ${name}` });
    }
  }
}
