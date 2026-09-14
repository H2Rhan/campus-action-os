import test from 'node:test';
import assert from 'node:assert/strict';
import { createApiError, loadSchema, protocolVersion } from '@campus-action-os/protocol';

test('protocol exposes a version without defining the final action schema', () => {
  assert.match(protocolVersion, /^\d+\.\d+\.\d+$/);
});

test('protocol loads local schemas offline and creates standard errors', () => {
  const vao = loadSchema('verified-action-object') as { $id?: string };
  const error = createApiError('EXAMPLE', 'Example error', 'request-123');
  assert.match(vao.$id ?? '', /verified-action-object/);
  assert.deepEqual(error, {
    error: {
      code: 'EXAMPLE',
      message: 'Example error',
      requestId: 'request-123',
      retryable: false,
    },
  });
});
