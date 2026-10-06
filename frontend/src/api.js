/**
 * Thin REST client over ctx.rest for the Agent Hold 'Em desktop plugin.
 *
 * ctx.rest(path, opts) throws on non-2xx with an Error whose `.statusCode`
 * carries the HTTP status (see apps/desktop/src/api/client.ts /
 * electron/api-transport.ts — httpStatusError sets `error.statusCode`, plus a
 * legacy "<status>: <body>" message). The backend's own error bodies are JSON
 * `{code, message}` (and 422 also carries `legal`) per docs/ARCHITECTURE.md §5,
 * but that body isn't exposed as structured data across the bridge — only via
 * the message string — so we defensively try to recover it from the message,
 * and always fall back to a safe generic shape.
 *
 * @typedef {Object} ApiError
 * @property {number} status
 * @property {string} code
 * @property {string} message
 * @property {any} [legal]
 */

/** @param {unknown} err @returns {ApiError} */
export function normalizeError(err) {
  // Electron's invoke bridge can discard Error.statusCode and keep only a
  // message like "Error invoking remote method ... Error: 404: {...}".
  // Recover the HTTP status before deciding what the user should do next.
  const rawMessage = err?.message ? String(err.message) : 'Request failed'
  const bridgedStatus = rawMessage.match(/(?:^|:\s)([45]\d\d):\s/)
  const status = typeof err?.statusCode === 'number' ? err.statusCode
    : typeof err?.status === 'number' ? err.status
    : bridgedStatus ? Number(bridgedStatus[1]) : 0
  let code = status === 409 ? 'stale' : status === 422 ? 'illegal' : 'error'
  let message = rawMessage
  let legal = undefined

  // Best-effort: the message is often "<status>: <json body>" — try to pull
  // the real backend {code, message, legal} out of it without ever throwing.
  const braceIdx = message.indexOf('{')
  if (braceIdx >= 0) {
    try {
      const parsed = JSON.parse(message.slice(braceIdx))
      if (parsed && typeof parsed === 'object') {
        if (typeof parsed.code === 'string') code = parsed.code
        if (typeof parsed.message === 'string') message = parsed.message
        else if (typeof parsed.detail === 'string') message = parsed.detail
        if (parsed.legal) legal = parsed.legal
      }
    } catch {
      // Not JSON — keep the raw message.
    }
  }

  if (status === 404 && message === 'Plugin not found') code = 'plugin_not_found'

  return { status, code, message, legal }
}

export function backendFailure(error) {
  if (error?.status === 404) {
    return {
      title: "Agent Hold 'Em isn't on this Hermes connection",
      description: "If Agent Hold 'Em is installed on this computer, choose This device in Hermes's connection switcher. Otherwise install and enable it on the selected connection. A new backend installation needs one restart."
    }
  }
  if (error?.status === 401 || error?.status === 403) {
    return {
      title: 'Hermes connection needs attention',
      description: 'Reconnect or sign in to the selected Hermes connection, then retry.'
    }
  }
  if (!error?.status) {
    return {
      title: "Can't reach the selected Hermes backend",
      description: 'Check the Hermes connection, then retry. The table will reconnect automatically when it becomes available.'
    }
  }
  return {
    title: "Agent Hold 'Em couldn't load",
    description: error?.message ?? 'The selected backend returned an error.'
  }
}

/**
 * Build a small typed-ish client bound to a ctx.rest function.
 * @param {(path: string, opts?: {method?: string, body?: unknown, timeoutMs?: number}) => Promise<any>} rest
 */
export function createApi(rest) {
  async function call(path, opts) {
    try {
      return await rest(path, opts)
    } catch (err) {
      throw normalizeError(err)
    }
  }

  return {
    /** @returns {Promise<{ok:boolean, version:string, engine:string, hermes:any}>} */
    health: () => call('/health'),
    /** @param {string} [profileId] @returns {Promise<{options: Array<{id:string,label:string,provider:string,model:string}>, default_id:string}>} */
    models: profileId => call(`/models${profileId ? `?profile=${encodeURIComponent(profileId)}` : ''}`),
    /** @returns {Promise<{profiles: Array<{id:string,name:string,label:string,avatar:any,model:string,provider:string}>}>} */
    profiles: () => call('/profiles'),
    /** @returns {Promise<any>} HumanView, see ARCHITECTURE.md §6 */
    state: () => call('/state'),
    /** @param {{opponents: Array<{profile_id:string,name:string,personality:string,model_id:string}>, decision_timeout_s?: number}} body */
    createTable: body => call('/table', { method: 'POST', body }),
    /** @param {{turn_id:string, expected_version:number, client_action_id:string, kind:string, to?:number}} body */
    action: body => call('/action', { method: 'POST', body }),
    /** @param {{text:string}} body */
    chat: body => call('/chat', { method: 'POST', body }),
    pause: () => call('/pause', { method: 'POST' }),
    resume: () => call('/resume', { method: 'POST' }),
    nextHand: () => call('/next-hand', { method: 'POST' }),
    /** @param {{confirm: true}} body */
    reset: body => call('/reset', { method: 'POST', body: body ?? { confirm: true } }),
    /** @param {number} [limit] */
    history: (limit = 20) => call(`/history?limit=${encodeURIComponent(limit)}`)
  }
}

/** crypto.randomUUID with a fallback for older embedders. */
export function newClientActionId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return 'caid-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10)
}
