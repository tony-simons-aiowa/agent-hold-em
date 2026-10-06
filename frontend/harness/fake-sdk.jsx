// Fake @hermes/plugin-sdk for the screenshot harness ONLY. Never shipped in
// the plugin bundle (build-frontend.sh externals the real specifier). Real
// react/react-dom/@tanstack/react-query are used underneath (symlinked from
// the Hermes checkout's node_modules — see scripts/build-harness.sh); only
// the Hermes-app-specific UI primitives and the `host`/`ctx` surface are
// approximated here, with plain CSS standing in for the app's real
// shadcn/radix components. Visual fidelity of THESE is secondary — the
// felt table itself is all `.ahe-*` CSS from the real plugin source.
import * as React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { atom, computed } from 'nanostores'
import { useStore } from '@nanostores/react'

export { useMutation, useQuery, useQueryClient, atom, computed }

export const ROUTES_AREA = 'routes'
export const SIDEBAR_NAV_AREA = 'sidebar.nav'
export const PALETTE_AREA = 'palette'
export const KEYBINDS_AREA = 'keybinds'
export const STATUSBAR_AREAS = { left: 'statusBar.left', right: 'statusBar.right' }

export function cn(...args) {
  return args.filter(Boolean).join(' ')
}

// A real, tiny nanostores-backed atom read: not used directly by our plugin
// (it uses React Query for server state) but exported for parity.
export function useValue(store) {
  return useStore(store)
}

const listeners = new Map()
export const host = {
  navigate(path) {
    window.dispatchEvent(new CustomEvent('harness:navigate', { detail: path }))
  },
  onEvent(type, fn) {
    const set = listeners.get(type) ?? new Set()
    set.add(fn)
    listeners.set(type, set)
    return () => set.delete(fn)
  },
  notify(input) {
    console.log('[harness host.notify]', input)
  },
  logs() {},
  status() {
    return {}
  },
  state: {
    viewport: atom({ width: window.innerWidth, height: window.innerHeight })
  }
}

/** Harness test hook: fire a fake gateway event. */
export function __harnessEmit(type, payload) {
  listeners.get(type)?.forEach(fn => fn(payload))
}

export function haptic() {}

// ---------------------------------------------------------------------------
// UI primitives (plain-CSS approximations; classNames namespaced `hx-` so
// they never collide with the plugin's own `.ahe-*` selectors).

export function Button({ children, variant = 'default', size = 'default', className, disabled, onClick, ...props }) {
  return (
    <button
      className={cn('hx-btn', `hx-btn-${variant}`, `hx-btn-${size}`, className)}
      disabled={disabled}
      onClick={onClick}
      {...props}
    >
      {children}
    </button>
  )
}

export function Input({ className, ...props }) {
  return <input className={cn('hx-input', className)} {...props} />
}

export function Blobatar({ name, size = 32 }) {
  return <span aria-hidden="true" style={{ display: 'grid', placeItems: 'center', width: size, height: size, borderRadius: '30%', background: '#8b5cf6', color: 'white' }}>{name?.slice(0, 1)?.toUpperCase()}</span>
}

export function Textarea({ className, ...props }) {
  return <textarea className={cn('hx-input', className)} {...props} />
}

export function SegmentedControl({ options, value, onChange, disabled, className }) {
  return (
    <div className={cn('hx-segmented', className)} data-disabled={String(!!disabled)}>
      {options.map(o => (
        <button
          key={o.id}
          type="button"
          className="hx-segmented-item"
          data-active={String(o.id === value)}
          disabled={disabled}
          onClick={() => onChange(o.id)}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

// A real Select (radix/shadcn-style) renders ONE control whose visible text
// is the matched option's *label*, not its raw value — the earlier version
// here rendered SelectValue's raw `value` (e.g. the id "default") stacked
// next to a second, separate native <select>, which is what produced the
// "raw text above the model select" bug this harness now avoids: Select is
// the single positioned control, SelectContent is an invisible native
// <select> overlaid on top of it (so it stays a real, keyboard/native-
// operable control), and SelectValue reads the CURRENT option's label out
// of context instead of ever printing the raw value.
const SelectCtx = React.createContext(null)
export function Select({ value, onValueChange, children }) {
  const [labels, setLabels] = React.useState({})
  return (
    <SelectCtx.Provider value={{ value, onValueChange, labels, setLabels }}>
      <div className="hx-select">{children}</div>
    </SelectCtx.Provider>
  )
}
export function SelectTrigger({ children, className, ...props }) {
  return (
    <div className={cn('hx-select-trigger', className)} {...props}>
      {children}
    </div>
  )
}
export function SelectValue({ placeholder }) {
  const ctx = React.useContext(SelectCtx)
  const label = ctx?.value != null ? ctx.labels[ctx.value] : undefined
  return <span className="hx-select-value">{label ?? placeholder ?? ''}</span>
}
export function SelectContent({ children }) {
  const ctx = React.useContext(SelectCtx)
  const items = React.Children.toArray(children)
  const key = items.map(el => `${el.props.value}:${el.props.children}`).join('|')
  React.useEffect(() => {
    const next = {}
    items.forEach(el => {
      next[el.props.value] = el.props.children
    })
    ctx?.setLabels(next)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])
  return (
    <select className="hx-select-native" value={ctx?.value ?? ''} onChange={e => ctx?.onValueChange?.(e.target.value)}>
      {children}
    </select>
  )
}
export function SelectItem({ value, children }) {
  return <option value={value}>{children}</option>
}

export function Badge({ children, variant = 'default', className, ...props }) {
  return (
    <span className={cn('hx-badge', `hx-badge-${variant}`, className)} {...props}>
      {children}
    </span>
  )
}

export function Kbd({ children }) {
  return <kbd className="hx-kbd">{children}</kbd>
}

export function ScrollArea({ children, className, ...props }) {
  return (
    <div className={cn('hx-scroll', className)} {...props}>
      {children}
    </div>
  )
}

export function GlyphSpinner({ ariaLabel = 'Loading' }) {
  return (
    <span className="ahe-spin" role="status" aria-label={ariaLabel}>
      ◐
    </span>
  )
}

export function StatusDot({ tone }) {
  return <span className={cn('hx-status-dot', `hx-status-${tone}`)} />
}

export function Codicon({ name, className, ...props }) {
  return <i className={cn('codicon', `codicon-${name}`, className)} aria-hidden="true" {...props} />
}

export function CopyButton({ text, label, showLabel, buttonVariant = 'ghost', buttonSize }) {
  return (
    <Button variant={buttonVariant} size={buttonSize} onClick={() => {}}>
      {label ?? 'Copy'}
    </Button>
  )
}

export function EmptyState({ title, description, className }) {
  return (
    <div className={cn('hx-empty', className)}>
      <div className="hx-empty-title">{title}</div>
      {description && <div className="hx-empty-desc">{description}</div>}
    </div>
  )
}

export function ErrorState({ title, description, children }) {
  return (
    <div className="hx-error">
      <div className="hx-empty-title">{title}</div>
      {description && <div className="hx-empty-desc">{description}</div>}
      {children && <div className="hx-error-actions">{children}</div>}
    </div>
  )
}

export function KbdGroup({ children }) {
  return <span className="hx-kbd-group">{children}</span>
}

export function Tip({ label, children }) {
  const [open, setOpen] = React.useState(false)
  return (
    <span
      className="hx-tip-wrap"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      {children}
      {open && label && <span className="hx-tip-bubble">{label}</span>}
    </span>
  )
}
export const Tooltip = Tip
export function TooltipContent({ children }) {
  return <>{children}</>
}
export function TooltipTrigger({ children }) {
  return <>{children}</>
}
export function TooltipProvider({ children }) {
  return <>{children}</>
}

export function ConfirmDialog({ open, onOpenChange, title, description, confirmLabel = 'Confirm', destructive, onConfirm }) {
  if (!open) return null
  return (
    <div className="hx-dialog-overlay" onClick={() => onOpenChange(false)}>
      <div className="hx-dialog" onClick={e => e.stopPropagation()}>
        <div className="hx-dialog-title">{title}</div>
        {description && <div className="hx-dialog-desc">{description}</div>}
        <div className="hx-dialog-actions">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant={destructive ? 'destructive' : 'default'}
            onClick={async () => {
              await onConfirm()
              onOpenChange(false)
            }}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  )
}
