import { useEffect, useState } from 'react'
import { Button, Input, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, SegmentedControl, Tip, useQuery } from '@hermes/plugin-sdk'
import { ProfileAvatar } from './ProfileAvatar.jsx'

const PERSONALITIES = [
  { id: 'cautious', label: 'Cautious', description: 'Plays few pots, folds to pressure without a strong hand.' },
  { id: 'balanced', label: 'Balanced', description: 'Mixes it up — no obvious pattern to exploit.' },
  { id: 'aggressive', label: 'Aggressive', description: 'Bets and raises often, applies pressure early.' }
]

function OpponentCard({ index, value, onChange, profiles, api }) {
  const profile = profiles.find(p => p.id === value.profile_id)
  const personaDesc = PERSONALITIES.find(p => p.id === value.personality)?.description
  const modelsQuery = useQuery({
    queryKey: ['agent-hold-em', 'models', value.profile_id],
    queryFn: () => api.models(value.profile_id),
    enabled: Boolean(value.profile_id),
    staleTime: 60_000
  })
  const modelOptions = modelsQuery.data?.options ?? []
  const [modelSearch, setModelSearch] = useState('')
  const query = modelSearch.trim().toLowerCase()
  const matchingModels = query
    ? modelOptions.filter(opt => `${opt.label} ${opt.id}`.toLowerCase().includes(query))
    : modelOptions
  const selectedModel = modelOptions.find(opt => opt.id === value.model_id)
  const visibleModels = matchingModels.slice(0, 25)
  if (selectedModel && !visibleModels.some(opt => opt.id === selectedModel.id)) visibleModels.unshift(selectedModel)

  return (
    <div className="ahe-oppo-card">
      <div className="ahe-oppo-head">
        <span aria-hidden="true"><ProfileAvatar avatar={profile?.avatar} size={36} /></span>
        <div className="ahe-profile-name">{profile?.name || `Opponent ${index + 1}`}</div>
      </div>

      <div className="ahe-field">
        <label className="ahe-field-label">Hermes profile</label>
        <Select value={value.profile_id} onValueChange={id => { setModelSearch(''); onChange({ ...value, profile_id: id, model_id: 'default' }) }}>
          <SelectTrigger aria-label={`Opponent ${index + 1} profile`}><SelectValue placeholder="Choose a profile" /></SelectTrigger>
          <SelectContent>
            {profiles.map(p => <SelectItem key={p.id} value={p.id}>{p.label}</SelectItem>)}
          </SelectContent>
        </Select>
        <div className="ahe-model-hint">Uses this profile's model connection and Bot Mode identity.</div>
      </div>

      <div className="ahe-field">
        <label className="ahe-field-label">Personality</label>
        <div className="ahe-segmented-wrap">
          <SegmentedControl value={value.personality} onChange={v => onChange({ ...value, personality: v })} options={PERSONALITIES} />
        </div>
        <div className="ahe-persona-desc">{personaDesc}</div>
      </div>

      <div className="ahe-field">
        <label className="ahe-field-label">Model</label>
        {modelOptions.length > 8 && (
          <Input aria-label={`Search opponent ${index + 1} models`} value={modelSearch}
            placeholder="Search provider or model" onChange={e => setModelSearch(e.target.value)} />
        )}
        <Select value={value.model_id} onValueChange={v => onChange({ ...value, model_id: v })}>
          <SelectTrigger aria-label={`Opponent ${index + 1} model`}><SelectValue placeholder={modelsQuery.isLoading ? 'Loading models…' : 'Choose a model'} /></SelectTrigger>
          <SelectContent>
            {visibleModels.map(opt => <SelectItem key={opt.id} value={opt.id}>{opt.label}</SelectItem>)}
          </SelectContent>
        </Select>
        {modelsQuery.isError && <div className="ahe-inline-error">Could not load this profile's models.</div>}
        {modelOptions.length > 8 && (
          <div className="ahe-model-hint">
            {matchingModels.length === 0
              ? 'No matching models.'
              : `${matchingModels.length} match${matchingModels.length === 1 ? '' : 'es'}${matchingModels.length > 25 ? ' — showing first 25' : ''}`}
          </div>
        )}
        {value.model_id === 'default' && <div className="ahe-model-hint">Uses this profile's default model.</div>}
      </div>
    </div>
  )
}

/** Three distinct local Hermes profiles, each with its own model and Bot Mode avatar. */
export function SetupScreen({ profilesData, profilesError, api, onSubmit, submitting, error }) {
  const profiles = profilesData?.profiles ?? []
  const [opponents, setOpponents] = useState(() => PERSONALITIES.map(p => ({ profile_id: '', personality: p.id, model_id: 'default' })))
  const [timeout_s, setTimeoutS] = useState(20)

  useEffect(() => {
    if (!profiles.length) return
    setOpponents(previous => {
      const used = new Set()
      return previous.map(opp => {
        const chosen = profiles.find(p => p.id === opp.profile_id && !used.has(p.id)) || profiles.find(p => !used.has(p.id))
        if (chosen) used.add(chosen.id)
        return { ...opp, profile_id: chosen?.id || '' }
      })
    })
  }, [profilesData])

  const selectedIds = opponents.map(o => o.profile_id).filter(Boolean)
  const ready = profiles.length >= 3 && selectedIds.length === 3 && new Set(selectedIds).size === 3

  function handleSubmit() {
    if (!ready) return
    onSubmit({
      opponents: opponents.map(o => ({
        profile_id: o.profile_id,
        name: profiles.find(p => p.id === o.profile_id)?.name || o.profile_id,
        personality: o.personality,
        model_id: o.model_id
      })),
      decision_timeout_s: timeout_s
    })
  }

  return (
    <div className="ahe-setup">
      <div className="ahe-setup-hero">
        <span className="ahe-live-chip" data-live="false">Bring your agents to the table</span>
        <p className="ahe-setup-honest">Choose three Hermes profiles. Their Bot Mode names and avatars come to the felt; each agent uses its own profile's model connection, with no tools or chat memory.</p>
      </div>

      <div className="ahe-rules-strip">
        <span>No-Limit Hold'Em</span><span>1,000 chips</span><span>Blinds 5 / 10</span><span>Play chips only — no real money</span>
      </div>

      {profilesError && <div className="ahe-inline-error">Could not load Hermes profiles: {profilesError}</div>}
      {!profilesData && !profilesError && <div className="ahe-model-hint">Loading Hermes profiles…</div>}
      {profilesData && profiles.length < 3 && <div className="ahe-inline-error">At least three local Hermes profiles are needed to start a table.</div>}
      <div className="ahe-setup-grid">
        {opponents.map((o, i) => (
          <OpponentCard key={i} index={i} value={o} profiles={profiles} api={api}
            onChange={next => setOpponents(prev => prev.map((p, idx) => {
              if (idx === i) return next
              if (next.profile_id !== o.profile_id && p.profile_id === next.profile_id) {
                return { ...p, profile_id: o.profile_id, model_id: 'default' }
              }
              return p
            }))} />
        ))}
      </div>

      <div className="ahe-setup-footer">
        <div className="ahe-field">
          <label className="ahe-field-label" htmlFor="ahe-timeout">Decision timeout (seconds)</label>
          <Tip label="How long each Hermes agent gets to decide before the table auto-folds (or checks) for it.">
            <Input id="ahe-timeout" type="number" min={5} max={60} value={timeout_s}
              onChange={e => setTimeoutS(Number(e.target.value) || 20)} style={{ width: '6rem' }} />
          </Tip>
        </div>
        <Button disabled={submitting || !ready} onClick={handleSubmit}>{submitting ? 'Dealing you in…' : 'Deal me in'}</Button>
      </div>
      {error && <div className="ahe-inline-error">{error}</div>}
    </div>
  )
}
