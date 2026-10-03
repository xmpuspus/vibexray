import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import OpenAI from 'openai';
import type {
  ChatCompletionMessage,
  ChatCompletionMessageParam,
  ChatCompletionMessageToolCall,
  ChatCompletionTool,
} from 'openai/resources/chat/completions';

/**
 * Thin wrapper around the LLM provider. Everything provider-specific lives here,
 * so swapping OpenAI for another backend only touches this file.
 */
@Injectable()
export class LlmService {
  private readonly logger = new Logger(LlmService.name);
  private readonly client: OpenAI;
  private readonly model: string;
  private readonly embeddingModel: string;

  constructor(private readonly config: ConfigService) {
    const apiKey = this.config.get<string>('openai.apiKey');
    if (!apiKey) {
      this.logger.warn('OPENAI_API_KEY is not set, requests will fail until it is configured.');
    }
    this.client = new OpenAI({ apiKey });
    this.model = this.config.get<string>('openai.model') ?? 'gpt-4o-mini';
    this.embeddingModel =
      this.config.get<string>('openai.embeddingModel') ?? 'text-embedding-3-small';
  }

  async embed(input: string[]): Promise<number[][]> {
    const res = await this.client.embeddings.create({ model: this.embeddingModel, input });
    return res.data.map((d) => d.embedding);
  }

  async chat(
    messages: ChatCompletionMessageParam[],
    tools?: ChatCompletionTool[],
  ): Promise<ChatCompletionMessage> {
    const hasTools = Boolean(tools && tools.length);
    const res = await this.client.chat.completions.create({
      model: this.model,
      messages,
      tools: hasTools ? tools : undefined,
      tool_choice: hasTools ? 'auto' : undefined,
      temperature: 0.2,
    });
    return res.choices[0].message;
  }

  /**
   * Streaming variant of chat(): yields content tokens as they arrive and
   * returns the fully assembled message (including any tool calls) when the
   * round completes, so callers can run the same tool loop either way.
   */
  async *chatStream(
    messages: ChatCompletionMessageParam[],
    tools?: ChatCompletionTool[],
  ): AsyncGenerator<string, ChatCompletionMessage> {
    const hasTools = Boolean(tools && tools.length);
    const stream = await this.client.chat.completions.create({
      model: this.model,
      messages,
      tools: hasTools ? tools : undefined,
      tool_choice: hasTools ? 'auto' : undefined,
      temperature: 0.2,
      stream: true,
    });

    let content = '';
    const toolCalls: ChatCompletionMessageToolCall[] = [];

    for await (const chunk of stream) {
      const delta = chunk.choices[0]?.delta;
      if (!delta) continue;

      if (delta.content) {
        content += delta.content;
        yield delta.content;
      }

      // Tool calls arrive as fragments keyed by index: the id and name come
      // once, the JSON arguments accumulate across chunks.
      for (const tc of delta.tool_calls ?? []) {
        const slot = (toolCalls[tc.index] ??= {
          id: '',
          type: 'function',
          function: { name: '', arguments: '' },
        });
        if (tc.id) slot.id = tc.id;
        if (tc.function?.name) slot.function.name = tc.function.name;
        if (tc.function?.arguments) slot.function.arguments += tc.function.arguments;
      }
    }

    return {
      role: 'assistant',
      content: content || null,
      tool_calls: toolCalls.length ? toolCalls : undefined,
    } as ChatCompletionMessage;
  }
}
