export type Scope = "memory:read" | "memory:write" | "memory:delete" | "memory:export" | "connections:manage";
export type ToolName = "memory.search" | "memory.write" | "memory.update" | "memory.forget";
export interface McpTransport { callTool<T>(name: ToolName, input: Record<string, unknown>, options?: { idempotencyKey?: string }): Promise<T>; }
export interface MemoryClient { search(input: Record<string, unknown>): Promise<unknown>; write(input: Record<string, unknown>, idempotencyKey: string): Promise<unknown>; update(input: Record<string, unknown>, idempotencyKey: string): Promise<unknown>; forget(input: Record<string, unknown>, idempotencyKey: string): Promise<unknown>; }
export function createMemoryClient(transport: McpTransport): MemoryClient;
