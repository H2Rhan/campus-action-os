import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

export const protocolVersion = '0.1.0';

export type RequestContext = {
  requestId: string;
  environment: 'local' | 'test' | 'demo' | 'production';
};
export type ApiError = {
  error: {
    code: string;
    message: string;
    requestId: string;
    retryable: boolean;
  };
};

/** Thin boundary type; field-level authority remains in schemas/v1. */
export type VerifiedActionObject = {
  schema_version: 'verified-action-object/v1';
  action_id: string;
  [field: string]: unknown;
};

/** Thin boundary type; field-level authority remains in schemas/v1. */
export type ActionGraph = {
  schema_version: 'action-graph/v1';
  graph_id: string;
  nodes: unknown[];
  edges: unknown[];
  [field: string]: unknown;
};

export type ProtocolSchemaName = 'verified-action-object' | 'action-graph' | 'campus-action-bench';

const schemaFiles: Record<ProtocolSchemaName, string> = {
  'verified-action-object': 'schemas/v1/verified-action-object.schema.json',
  'action-graph': 'schemas/v1/action-graph.schema.json',
  'campus-action-bench': 'benchmark/schema/campus-action-bench-v1.schema.json',
};

export function getSchemaPath(name: ProtocolSchemaName, rootDir = process.cwd()): string {
  return resolve(rootDir, schemaFiles[name]);
}

export function loadSchema(name: ProtocolSchemaName, rootDir = process.cwd()): unknown {
  // Keep loading local and offline; consumers decide which validator to use.
  return JSON.parse(readFileSync(getSchemaPath(name, rootDir), 'utf8')) as unknown;
}

export function createApiError(
  code: string,
  message: string,
  requestId: string,
  retryable = false,
): ApiError {
  return { error: { code, message, requestId, retryable } };
}
