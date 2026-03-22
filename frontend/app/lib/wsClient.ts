"use client";

export type ServerMessageType =
  | "session_created"
  | "storybook_created"
  | "agent_thinking"
  | "agent_stream_start"
  | "agent_stream_chunk"
  | "agent_stream_end"
  | "agent_idle"
  | "tool_status"
  | "scene_add"
  | "scene_update"
  | "scene_remove"
  | "error";

export interface ServerMessage {
  readonly type: ServerMessageType;
  readonly [key: string]: unknown;
}

export type MessageHandler = (msg: ServerMessage) => void;

const DEFAULT_WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:3001/ws";
const RECONNECT_DELAY_MS = 2000;
const MAX_RECONNECT_ATTEMPTS = 5;

export class WSClient {
  private ws: WebSocket | null = null;
  private readonly url: string;
  private handler: MessageHandler | null = null;
  private onReadyCallback: (() => void) | null = null;
  private reconnectAttempts = 0;
  private shouldReconnect = true;

  constructor(url: string = DEFAULT_WS_URL) {
    this.url = url;
  }

  connect(handler: MessageHandler, onReady?: () => void): void {
    this.handler = handler;
    this.onReadyCallback = onReady ?? null;
    this.shouldReconnect = true;
    this.reconnectAttempts = 0;
    this.createConnection();
  }

  private createConnection(): void {
    console.debug("[SayCut] WS connecting to", this.url);
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.debug("[SayCut] WS connected");
      this.reconnectAttempts = 0;
      this.onReadyCallback?.();
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data as string) as ServerMessage;
        console.debug("[SayCut] WS recv:", msg.type);
        this.handler?.(msg);
      } catch {
        console.debug("[SayCut] WS unparseable message");
      }
    };

    this.ws.onclose = () => {
      console.debug("[SayCut] WS closed");
      if (
        this.shouldReconnect &&
        this.reconnectAttempts < MAX_RECONNECT_ATTEMPTS
      ) {
        this.reconnectAttempts++;
        console.debug(
          "[SayCut] WS reconnecting, attempt",
          this.reconnectAttempts,
        );
        setTimeout(() => this.createConnection(), RECONNECT_DELAY_MS);
      }
    };

    this.ws.onerror = () => {
      console.debug("[SayCut] WS error");
    };
  }

  send(data: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.debug("[SayCut] WS send:", data.type);
      this.ws.send(JSON.stringify(data));
    }
  }

  sendSessionInit(sessionId?: string): void {
    const payload: Record<string, unknown> = { type: "session_init" };
    if (sessionId) {
      payload.session_id = sessionId;
    }
    this.send(payload);
  }

  sendAudioData(base64Data: string): void {
    this.send({ type: "audio_data", data: base64Data });
  }

  sendTextMessage(text: string): void {
    this.send({ type: "text_message", text });
  }

  sendLoadStorybook(storybookId: string): void {
    this.send({ type: "load_storybook", storybook_id: storybookId });
  }

  sendSetProjectMode(
    mode: string,
    characters?: readonly { name: string; voice: string }[],
  ): void {
    const payload: Record<string, unknown> = {
      type: "set_project_mode",
      mode,
    };
    if (characters) {
      payload.characters = characters;
    }
    this.send(payload);
  }

  disconnect(): void {
    console.debug("[SayCut] WS disconnecting");
    this.shouldReconnect = false;
    this.ws?.close();
    this.ws = null;
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
