import { useState } from 'react'
import {
  Button,
  ErrorState,
  GlyphSpinner,
  PALETTE_AREA,
  ROUTES_AREA,
  SIDEBAR_NAV_AREA,
  STATUSBAR_AREAS,
  host,
  useQuery
} from '@hermes/plugin-sdk'
import { backendFailure, createApi } from './api.js'
import { ensureStyles } from './styles.js'
import { SetupScreen } from './components/SetupScreen.jsx'
import { TableScreen } from './components/TableScreen.jsx'
import { useTableState } from './hooks.js'

const ID = 'agent-hold-em'
const PATH = '/agent-hold-em'

// One api client per ctx.rest (register() supplies it) — module scope so
// every component under this page shares the same instance without prop
// threading a fresh object down from the root every render. `storage` is
// ctx.storage itself (get/set/remove), used for small per-viewer prefs
// (currently just the 4-color deck toggle) — never for table state, which
// always comes from the backend.
let api = null
let storage = null

function Page() {
  const [globalError, setGlobalError] = useState(null)
  const stateQuery = useTableState(api)
  const profilesQuery = useQuery({
    queryKey: ['agent-hold-em', 'profiles'],
    queryFn: () => api.profiles(),
    enabled: stateQuery.isSuccess && stateQuery.data?.status === 'setup',
    staleTime: 60_000
  })
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState(null)

  if (stateQuery.isLoading) {
    return (
      <div className="ahe-root">
        <div className="ahe-center-state">
          <GlyphSpinner ariaLabel="Loading Agent Hold 'Em" />
        </div>
      </div>
    )
  }

  if (stateQuery.isError) {
    const failure = backendFailure(stateQuery.error)
    return (
      <div className="ahe-root">
        <div className="ahe-center-state">
          <ErrorState
            title={failure.title}
            description={failure.description}
          >
            <Button onClick={() => stateQuery.refetch()}>Retry</Button>
          </ErrorState>
        </div>
      </div>
    )
  }

  const view = stateQuery.data

  if (!view || view.status === 'setup') {
    return (
      <div className="ahe-root">
        <SetupScreen
          profilesData={profilesQuery.data}
          profilesError={profilesQuery.isError ? profilesQuery.error?.message : null}
          api={api}
          submitting={creating}
          error={createError}
          onSubmit={async body => {
            setCreating(true)
            setCreateError(null)
            try {
              await api.createTable(body)
              await stateQuery.refetch()
            } catch (err) {
              setCreateError(err.message ?? 'Could not start the table.')
            } finally {
              setCreating(false)
            }
          }}
        />
      </div>
    )
  }

  // 'finished'/'paused' reuse the same felt view (winner's stack, final board
  // still visible) with an overlay on top — see TableScreen — rather than a
  // second stacked screen, which used to squeeze the felt tall enough to
  // overlap seats at short viewport heights.
  return <TableScreen api={api} view={view} storage={storage} onError={e => setGlobalError(e?.message)} />
}

/** Command-palette + status bar chip need a lightweight read of table status
 *  without mounting the full page — a tiny standalone query on the same key. */
function StatusChip() {
  const query = useQuery({
    queryKey: ['agent-hold-em', 'state'],
    queryFn: () => api.state(),
    refetchInterval: query => query.state.status === 'error' ? 30_000 : 5000,
    enabled: api != null
  })
  const view = query.data
  if (!view || view.status !== 'running') return null
  return (
    <span>
      ♠ Hand {view.hand_no} · {view.to_act === view.seats.find(s => s.kind === 'human')?.seat ? 'Your turn' : 'Agents playing'}
    </span>
  )
}

const plugin = {
  id: ID,
  name: "Agent Hold 'Em",
  description: "Play No-Limit Hold'Em against three real Hermes agents.",
  register(ctx) {
    api = createApi(ctx.rest)
    storage = ctx.storage
    ensureStyles()

    ctx.registerMany([
      { id: 'page', area: ROUTES_AREA, data: { path: PATH }, render: () => <Page /> },
      {
        id: 'nav',
        area: SIDEBAR_NAV_AREA,
        data: { path: PATH, label: "Agent Hold 'Em", codicon: 'game' }
      },
      {
        id: 'open',
        area: PALETTE_AREA,
        data: {
          id: 'agent-hold-em.open',
          label: "Agent Hold 'Em: Open table",
          keywords: ['poker', 'holdem', 'agent', 'hermes', 'cards'],
          run: () => host.navigate(PATH)
        }
      },
      {
        id: 'pause-resume',
        area: PALETTE_AREA,
        data: {
          id: 'agent-hold-em.pause-resume',
          label: "Agent Hold 'Em: Pause/Resume table",
          keywords: ['poker', 'pause', 'resume'],
          run: async () => {
            const view = await api.state()
            if (view.status === 'running') await api.pause()
            else if (view.status === 'paused') await api.resume()
          }
        }
      },
      {
        id: 'new-table',
        area: PALETTE_AREA,
        data: {
          id: 'agent-hold-em.new-table',
          label: "Agent Hold 'Em: New table",
          keywords: ['poker', 'reset', 'new game'],
          run: () => api.reset({ confirm: true })
        }
      },
      {
        id: 'statusbar',
        area: STATUSBAR_AREAS.right,
        order: 140,
        render: () => <StatusChip />
      }
    ])
  }
}

export default plugin
