export type Entity = {
  text: string;
  label: string;
};

export type Source = {
  question: string;
  link?: string;
  source?: string;
  distance?: number;
};

export type Topic = {
  allowed: boolean;
  distance: number;
  zone: string;
  reason?: string;
};

export type Stats = {
  prompt_tokens?: number | null;
  gen_tokens?: number | null;
  prompt_s?: number | null;
  gen_s?: number | null;
  provider?: string;
  model?: string;
  ttft_s?: number | null;
  total_s?: number | null;
};

export type ModelOption = {
  id: string;
  label: string;
  model: string;
  ready: boolean;
  note: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: number;
  entities?: Entity[];
  sources?: Source[];
  topic?: Topic;
  stats?: Stats;
  error?: boolean;
  pending?: boolean;
};

export type Conversation = {
  id: string;
  title: string;
  createdAt: number;
  messages: ChatMessage[];
};

export type ChatEvent =
  | { type: "meta"; entities?: Entity[]; topic?: Topic }
  | { type: "static"; text: string }
  | { type: "text"; text: string }
  | {
      type: "final";
      allowed?: boolean;
      sources?: Source[];
      stats?: Stats;
      topic?: Topic;
      error?: boolean;
    }
  | { type: "error"; message: string };
