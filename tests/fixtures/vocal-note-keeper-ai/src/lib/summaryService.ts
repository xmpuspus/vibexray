
import { Settings } from './database';
import OpenAI from 'openai';

export interface SummaryResult {
  title: string;
  summary: string;
}

export const SUMMARY_PROVIDERS = [
  { name: 'none', displayName: 'No Summary', requiresApiKey: false },
  { name: 'openai', displayName: 'OpenAI GPT', requiresApiKey: true },
  { name: 'lmstudio', displayName: 'LM Studio (Local)', requiresApiKey: false }
];

export const generateSummary = async (transcript: string, settings: Settings): Promise<SummaryResult> => {
  console.log('Generating summary with provider:', settings.summaryProvider);
  
  if (!settings.summaryProvider || settings.summaryProvider === 'none') {
    throw new Error('Summary provider not configured');
  }

  switch (settings.summaryProvider) {
    case 'openai':
      return generateOpenAISummary(transcript, settings);
    case 'lmstudio':
      return generateLMStudioSummary(transcript, settings);
    default:
      throw new Error(`Unsupported summary provider: ${settings.summaryProvider}`);
  }
};

const generateOpenAISummary = async (transcript: string, settings: Settings): Promise<SummaryResult> => {
  if (!settings.openaiApiKey) {
    throw new Error('OpenAI API key not configured');
  }

  console.log('Making OpenAI API request...');
  
  const openai = new OpenAI({
    apiKey: settings.openaiApiKey,
    dangerouslyAllowBrowser: true
  });

  const response = await openai.chat.completions.create({
    model: settings.summaryModel || 'gpt-4o-mini',
    messages: [
      {
        role: 'system',
        content: 'You are a helpful summary assistant'
      },
      {
        role: 'user',
        content: `You are a helpful summary assistant, summaries the following meeting transcript into bullets for "summary", and using summary decide on a "title" (include pun if possible, max 50 characters ). You must respond in json! Transcript: ${transcript} \n You must respond in JSON with summary and title key's`
      }
    ],
    max_tokens: 500,
    temperature: 0.6,
    response_format: {
      type: "json_schema",
      json_schema: {
        name: "summary",
        schema: {
          type: "object",
          properties: {
            title: {
              type: "string"
            },
            summary: {
              type: "string"
            }
          },
          required: ["title", "summary"]
        }
      }
    }
  });

  console.log('OpenAI response:', response);
  const parsed = JSON.parse(response.choices[0].message.content || '{}');
  
  return {
    title: parsed.title,
    summary: parsed.summary
  };
};

const generateLMStudioSummary = async (transcript: string, settings: Settings): Promise<SummaryResult> => {
  const serverUrl = settings.lmstudioServerUrl || 'http://192.168.0.11:1234';
  
  console.log('Making LM Studio API request to:', serverUrl);
  
  if (!settings.summaryModel) {
    throw new Error('Model is required for LM Studio');
  }

  const openai = new OpenAI({
    baseURL: `${serverUrl}/v1`,
    apiKey: 'lm-studio',
    dangerouslyAllowBrowser: true
  });

  try {
    const response = await openai.chat.completions.create({
      model: settings.summaryModel,
      messages: [
        {
          role: 'system',
          content: 'You are a helpful summary assistant'
        },
        {
          role: 'user',
          content: `You are a helpful summary assistant, summaries the following meeting transcript into bullets for "summary", and using summary decide on a "title" (include pun if possible, max 50 characters ). You must respond in json! Transcript: ${transcript} \n You must respond in JSON with summary and title key's`
        }
      ],
      max_tokens: 500,
      temperature: 0.6,
      response_format: {
        type: "json_schema",
        json_schema: {
          name: "summary",
          schema: {
            type: "object",
            properties: {
              title: {
                type: "string"
              },
              summary: {
                type: "string"
              }
            },
            required: ["title", "summary"]
          }
        }
      }
    });

    console.log('LM Studio response:', response);
    const parsed = JSON.parse(response.choices[0].message.content || '{}');
    
    return {
      title: parsed.title || 'Generated Summary',
      summary: parsed.summary || response.choices[0].message.content || ''
    };
  } catch (error) {
    console.error('LM Studio request failed:', error);
    if (error instanceof Error) {
      throw new Error(`LM Studio connection failed: ${error.message}. Make sure LM Studio is running on ${serverUrl} with the model loaded.`);
    }
    throw new Error('LM Studio connection failed. Make sure LM Studio is running with the model loaded.');
  }
};
