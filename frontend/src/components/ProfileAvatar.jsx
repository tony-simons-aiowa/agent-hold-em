import { Blobatar } from '@hermes/plugin-sdk'

const BLOB_KIND_TRAIT = {
  round: 0.11, organic: 0.35, boxy: 0.54, capsule: 0.65, nub: 0.745,
  cloud: 0.825, droplet: 0.8875, hexagon: 0.9325, sun: 0.965, triangle: 0.99
}

/** The profile's Bot Mode asset wins; Blobatar is the fallback for a new shape. */
export function ProfileAvatar({ avatar, size = 32 }) {
  if (typeof avatar === 'string') return <span>{avatar}</span> // older saved tables
  if (avatar?.image_kind !== 'photo' && avatar?.shape?.startsWith('blobatar')) {
    const [, pinnedSeed, kind] = avatar.shape.split(':')
    const traits = BLOB_KIND_TRAIT[kind] == null ? undefined : { shape: BLOB_KIND_TRAIT[kind] }
    return <Blobatar name={pinnedSeed || avatar.seed || 'agent'} size={size} traits={traits} alt="" />
  }
  if (avatar?.image) {
    return <img src={avatar.image} alt="" width={size} height={size} style={{ display: 'block', width: size, height: size, borderRadius: '22%', objectFit: 'cover' }} />
  }
  return (
    <span className="ahe-avatar-fallback" style={{ width: size, height: size, background: avatar?.color || '#8b5cf6' }}>
      {(avatar?.seed || '?').slice(0, 1).toUpperCase()}
    </span>
  )
}
