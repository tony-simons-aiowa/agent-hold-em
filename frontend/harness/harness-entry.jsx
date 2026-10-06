// Screenshot harness entry point. Loads the REAL built plugin bundle
// (../../package/agent-hold-em/desktop/plugin.js) with '@hermes/plugin-sdk'
// aliased (via esbuild --alias) to fake-sdk.jsx, mounts its ROUTES_AREA page,
// and serves scripted HumanView fixtures through a fake ctx.rest so every
// state can be captured without a running Hermes backend.
import * as React from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import plugin from '../src/index.jsx'
import { FIXTURES, MODELS_FIXTURE, PROFILES_FIXTURE } from './fixtures.js'
// harness.css is linked directly from index.html (kept out of the JS bundle
// so the esbuild invocation here never has to deal with CSS loaders).

function currentParams() {
  const p = new URLSearchParams(window.location.search)
  return {
    fixture: p.get('fixture') || 'preflop_turn',
    theme: p.get('theme') || 'light',
    chrome: p.get('chrome') !== '0' // set chrome=0 to hide the control bar for clean screenshots
  }
}

function applyTheme(theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark')
}

const contributions = { routes: [], 'sidebar.nav': [], palette: [], 'statusBar.right': [] }

function fakeRest(path) {
  const clean = path.split('?')[0]
  const { fixture } = currentParams()
  if (clean === '/profiles') return Promise.resolve(PROFILES_FIXTURE)
  if (clean === '/models') {
    if (new URLSearchParams(window.location.search).get('models') === 'many') {
      return Promise.resolve({
        ...MODELS_FIXTURE,
        options: [
          ...MODELS_FIXTURE.options,
          ...Array.from({ length: 30 }, (_, i) => ({
            id: `openai-codex:fixture-model-${i + 1}`,
            label: `ChatGPT or Codex Subscription — fixture-model-${i + 1}`,
            provider: 'openai-codex',
            model: `fixture-model-${i + 1}`
          }))
        ]
      })
    }
    return Promise.resolve(MODELS_FIXTURE)
  }
  if (clean === '/state') {
    const data = FIXTURES[fixture]
    if (fixture === 'backend_missing') {
      return Promise.reject(new Error('Error invoking remote method \'hermes:api\': Error: 404: {"detail":"Plugin not found"}'))
    }
    if (data?.__isError) return Promise.reject(Object.assign(new Error('Hermes desktop bridge unavailable'), { statusCode: 0 }))
    if (fixture === 'setup') return Promise.resolve({ schema: 1, status: 'setup', seats: [] })
    return Promise.resolve(data)
  }
  if (clean === '/health') return Promise.resolve({ ok: true, version: 'harness', engine: 'native', hermes: {} })
  // Setup submit / actions: no-op success in the harness (visual only).
  return Promise.resolve(FIXTURES[currentParams().fixture] ?? {})
}

const ctx = {
  register(contribution) {
    const area = contributions[contribution.area] ?? (contributions[contribution.area] = [])
    area.push(contribution)
    return () => {}
  },
  registerMany(list) {
    list.forEach(c => ctx.register(c))
    return () => {}
  },
  onDispose() {},
  onEvent() {
    return () => {}
  },
  setTimeout: (fn, ms) => {
    const id = window.setTimeout(fn, ms)
    return () => window.clearTimeout(id)
  },
  setInterval: (fn, ms) => {
    const id = window.setInterval(fn, ms)
    return () => window.clearInterval(id)
  },
  addEventListener: (target, type, listener) => {
    target.addEventListener(type, listener)
    return () => target.removeEventListener(type, listener)
  },
  rest: fakeRest,
  socket: () => () => {},
  os: {
    notify: () => {},
    openExternal: async () => false,
    revealPath: async () => false,
    pickSavePath: async () => null,
    pickOpenPath: async () => null,
    writeClipboard: async () => true
  },
  // Real persistence (localStorage) in the harness so the 4-color-deck
  // toggle is actually screenshot-able across a reload — the real ctx.storage
  // is per-viewer/local exactly like this, per ARCHITECTURE.md/CONTRACT.md.
  storage: {
    get: (key, fallback) => {
      try {
        const raw = window.localStorage.getItem(`ahe-harness:${key}`)
        return raw == null ? fallback : JSON.parse(raw)
      } catch {
        return fallback
      }
    },
    set: (key, value) => {
      try {
        window.localStorage.setItem(`ahe-harness:${key}`, JSON.stringify(value))
      } catch {
        // best-effort
      }
    },
    remove: key => {
      try {
        window.localStorage.removeItem(`ahe-harness:${key}`)
      } catch {
        // best-effort
      }
    }
  },
  i18n: {
    register() {},
    t: key => key
  }
}

plugin.register(ctx)

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } }
})

function ControlBar({ params, onChange }) {
  return (
    <div className="hx-controlbar">
      <strong>{plugin.name} harness</strong>
      <label>
        Fixture:
        <select value={params.fixture} onChange={e => onChange({ fixture: e.target.value })}>
          {Object.keys(FIXTURES).map(k => (
            <option key={k} value={k}>
              {k}
            </option>
          ))}
        </select>
      </label>
      <label>
        Theme:
        <select value={params.theme} onChange={e => onChange({ theme: e.target.value })}>
          <option value="light">Light</option>
          <option value="dark">Dark</option>
        </select>
      </label>
    </div>
  )
}

function Harness() {
  const [params, setParams] = React.useState(currentParams())

  React.useEffect(() => {
    applyTheme(params.theme)
  }, [params.theme])

  function update(patch) {
    const next = { ...params, ...patch }
    setParams(next)
    const search = new URLSearchParams({ fixture: next.fixture, theme: next.theme, chrome: next.chrome ? '1' : '0' })
    window.history.replaceState(null, '', `?${search.toString()}`)
  }

  const route = contributions.routes.find(r => r.data.path === '/agent-hold-em')

  return (
    <QueryClientProvider client={queryClient}>
      <div className="hx-page-shell" key={params.fixture}>
        {params.chrome && <ControlBar params={params} onChange={update} />}
        {/* Block, not flex: `.ahe-root` sizes itself with height:100% / width:auto
            against a definite parent box. A `display:flex` wrapper here would
            leave `.ahe-root` sized to its content on the main axis (no
            `flex-grow` of its own) — exactly the "column of nothing" bug this
            comment is guarding against; it collapsed the felt table to a
            vertical sliver in an earlier harness build. */}
        <div style={{ flex: '1 1 auto', minHeight: 0, position: 'relative' }}>
          {route ? route.render() : <p>No route registered.</p>}
        </div>
      </div>
    </QueryClientProvider>
  )
}

createRoot(document.getElementById('root')).render(<Harness />)
