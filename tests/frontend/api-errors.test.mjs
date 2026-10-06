import assert from 'node:assert/strict'
import { test } from 'node:test'

import { backendFailure, normalizeError } from '../../frontend/src/api.js'

test('recovers a missing-plugin response after Electron strips Error.statusCode', () => {
  const error = normalizeError(new Error(
    'Error invoking remote method \'hermes:api\': Error: 404: {"detail":"Plugin not found"}'
  ))
  assert.equal(error.status, 404)
  assert.equal(error.code, 'plugin_not_found')
  assert.match(backendFailure(error).description, /choose This device/)
})

test('keeps a network failure distinct from a missing plugin', () => {
  const error = normalizeError(new Error('connect ECONNREFUSED 127.0.0.1:9119'))
  assert.equal(error.status, 0)
  assert.match(backendFailure(error).title, /reach the selected Hermes backend/)
})

test('preserves structured backend errors', () => {
  const error = normalizeError(Object.assign(new Error('422: {"code":"illegal","message":"Invalid action"}'), {
    statusCode: 422
  }))
  assert.deepEqual({ status: error.status, code: error.code, message: error.message }, {
    status: 422, code: 'illegal', message: 'Invalid action'
  })
})
