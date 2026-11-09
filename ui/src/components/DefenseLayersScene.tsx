import {
  ContactShadows,
  Environment,
  Float,
  OrbitControls,
  Sparkles,
} from '@react-three/drei'
import { Canvas, useFrame } from '@react-three/fiber'
import { useMemo, useRef } from 'react'
import type { Group, Mesh } from 'three'
import * as THREE from 'three'
import type { GuardEventTrace, GuardLayerInfo } from '../api'

export type LayerId = 'user_input' | 'retrieved_context' | 'tool_output'
export type LayerStatus = 'idle' | 'allow' | 'block' | 'drop' | 'flag'

const LAYER_ORDER: LayerId[] = ['user_input', 'retrieved_context', 'tool_output']

const LAYER_META: Record<
  LayerId,
  { label: string; radius: number; y: number; short: string }
> = {
  user_input: { label: 'User input', radius: 1.35, y: 1.15, short: 'INPUT' },
  retrieved_context: {
    label: 'Retrieved context',
    radius: 2.05,
    y: 0.05,
    short: 'CONTEXT',
  },
  tool_output: { label: 'Tool output', radius: 2.75, y: -1.05, short: 'TOOLS' },
}

export function getLayerStatus(
  layerId: LayerId,
  events: GuardEventTrace[],
): LayerStatus {
  const matches = events.filter((event) => event.layer === layerId)
  if (matches.length === 0) return 'idle'
  if (matches.some((event) => event.action === 'block')) return 'block'
  if (matches.some((event) => event.action === 'drop')) return 'drop'
  if (matches.some((event) => event.action === 'flag')) return 'flag'
  return 'allow'
}

function statusPalette(status: LayerStatus, enabled: boolean) {
  if (!enabled) {
    return { color: '#8b97a8', emissive: '#2a3340', intensity: 0.05 }
  }
  switch (status) {
    case 'block':
    case 'drop':
      return { color: '#d3541a', emissive: '#9a3412', intensity: 0.55 }
    case 'flag':
      return { color: '#d97706', emissive: '#92400e', intensity: 0.4 }
    case 'allow':
      return { color: '#14a3ad', emissive: '#0b7f8a', intensity: 0.45 }
    default:
      return { color: '#5d6b7c', emissive: '#1f2a37', intensity: 0.12 }
  }
}

function DecisionCore({ hot }: { hot: boolean }) {
  const core = useRef<Mesh>(null)
  const ring = useRef<Mesh>(null)

  useFrame((_, delta) => {
    if (core.current) core.current.rotation.y += delta * (hot ? 1.2 : 0.35)
    if (ring.current) {
      ring.current.rotation.z -= delta * (hot ? 0.9 : 0.25)
      ring.current.rotation.x = Math.PI / 2.4
    }
  })

  return (
    <Float speed={hot ? 2.2 : 1.1} rotationIntensity={0.15} floatIntensity={0.35}>
      <mesh ref={core}>
        <dodecahedronGeometry args={[0.42, 0]} />
        <meshStandardMaterial
          color={hot ? '#0d9488' : '#3d4b5c'}
          emissive={hot ? '#0b7f8a' : '#15202b'}
          emissiveIntensity={hot ? 0.7 : 0.2}
          metalness={0.55}
          roughness={0.22}
        />
      </mesh>
      <mesh ref={ring} scale={[1.35, 1.35, 1.35]}>
        <torusGeometry args={[0.55, 0.035, 16, 64]} />
        <meshStandardMaterial
          color="#0b7f8a"
          emissive="#066069"
          emissiveIntensity={hot ? 0.6 : 0.2}
          metalness={0.4}
          roughness={0.3}
        />
      </mesh>
      {hot && (
        <Sparkles
          count={28}
          scale={2.2}
          size={2.5}
          speed={0.5}
          color="#5eead4"
          opacity={0.55}
        />
      )}
    </Float>
  )
}

function GateRing({
  layerId,
  enabled,
  status,
  selected,
  onSelect,
}: {
  layerId: LayerId
  enabled: boolean
  status: LayerStatus
  selected: boolean
  onSelect: (id: LayerId) => void
}) {
  const group = useRef<Group>(null)
  const meta = LAYER_META[layerId]
  const palette = statusPalette(status, enabled)
  const mat = useRef<THREE.MeshStandardMaterial>(null)

  useFrame((state) => {
    if (!group.current) return
    const t = state.clock.elapsedTime
    group.current.rotation.y = t * (selected ? 0.18 : 0.08)
    if (status !== 'idle' && mat.current) {
      mat.current.emissiveIntensity =
        palette.intensity + Math.sin(t * 4) * 0.12
    }
  })

  return (
    <group
      ref={group}
      position={[0, meta.y, 0]}
      onClick={(event) => {
        event.stopPropagation()
        onSelect(layerId)
      }}
      onPointerOver={(event) => {
        event.stopPropagation()
        document.body.style.cursor = 'pointer'
      }}
      onPointerOut={() => {
        document.body.style.cursor = 'default'
      }}
    >
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[meta.radius, selected ? 0.07 : 0.045, 20, 96]} />
        <meshStandardMaterial
          ref={mat}
          color={palette.color}
          emissive={palette.emissive}
          emissiveIntensity={palette.intensity}
          metalness={0.35}
          roughness={0.28}
          transparent
          opacity={enabled ? 0.95 : 0.35}
        />
      </mesh>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[meta.radius - 0.22, meta.radius - 0.08, 64]} />
        <meshStandardMaterial
          color={palette.color}
          transparent
          opacity={selected ? 0.22 : 0.08}
          side={THREE.DoubleSide}
        />
      </mesh>
      {/* node markers on the ring */}
      {[0, 1, 2, 3].map((i) => {
        const a = (i / 4) * Math.PI * 2
        return (
          <mesh
            key={i}
            position={[Math.cos(a) * meta.radius, 0, Math.sin(a) * meta.radius]}
          >
            <sphereGeometry args={[0.06, 16, 16]} />
            <meshStandardMaterial
              color={palette.color}
              emissive={palette.emissive}
              emissiveIntensity={selected ? 0.7 : 0.25}
            />
          </mesh>
        )
      })}
    </group>
  )
}

function ScanBeam({
  targetY,
  active,
  status,
}: {
  targetY: number
  active: boolean
  status: LayerStatus
}) {
  const ref = useRef<Mesh>(null)
  const palette = statusPalette(status, true)

  useFrame((state) => {
    if (!ref.current) return
    const pulse = 0.35 + Math.sin(state.clock.elapsedTime * 5) * 0.15
    const mat = ref.current.material as THREE.MeshBasicMaterial
    mat.opacity = active ? pulse : 0.05
  })

  return (
    <mesh ref={ref} position={[0, targetY / 2, 0]}>
      <cylinderGeometry args={[0.02, 0.02, Math.abs(targetY) + 0.01, 8]} />
      <meshBasicMaterial
        color={palette.color}
        transparent
        opacity={active ? 0.45 : 0.05}
      />
    </mesh>
  )
}

function Scene({
  enabledMap,
  events,
  selected,
  onSelect,
}: {
  enabledMap: Record<LayerId, boolean>
  events: GuardEventTrace[]
  selected: LayerId | null
  onSelect: (id: LayerId) => void
}) {
  const hot = events.some((event) => event.injection)

  return (
    <>
      <color attach="background" args={['#0f141b']} />
      <fog attach="fog" args={['#0f141b', 8, 18]} />
      <ambientLight intensity={0.35} />
      <directionalLight position={[5, 8, 4]} intensity={1.1} color="#e8eef5" />
      <pointLight position={[0, 2.5, 0]} intensity={1.2} color="#14b8a6" distance={8} />
      <pointLight position={[-3, -1, 2]} intensity={0.35} color="#94a3b8" distance={7} />

      <DecisionCore hot={hot} />

      {LAYER_ORDER.map((id) => {
        const status = getLayerStatus(id, events)
        return (
          <group key={id}>
            <GateRing
              layerId={id}
              enabled={enabledMap[id]}
              status={status}
              selected={selected === id}
              onSelect={onSelect}
            />
            <ScanBeam
              targetY={LAYER_META[id].y}
              active={status !== 'idle'}
              status={status}
            />
          </group>
        )
      })}

      <ContactShadows
        position={[0, -1.75, 0]}
        opacity={0.45}
        scale={10}
        blur={2.5}
        far={4}
      />
      <Environment preset="city" environmentIntensity={0.35} />
      <OrbitControls
        makeDefault
        enablePan={false}
        minDistance={4}
        maxDistance={12}
        maxPolarAngle={Math.PI / 1.85}
        autoRotate
        autoRotateSpeed={0.45}
        target={[0, 0.05, 0]}
      />
    </>
  )
}

export function DefenseLayersScene({
  guardLayers,
  events,
  selected,
  onSelect,
}: {
  guardLayers: GuardLayerInfo[]
  events: GuardEventTrace[]
  selected: LayerId | null
  onSelect: (id: LayerId) => void
}) {
  const enabledMap = useMemo(() => {
    const map: Record<LayerId, boolean> = {
      user_input: true,
      retrieved_context: true,
      tool_output: true,
    }
    for (const layer of guardLayers) {
      if (layer.id in map) {
        map[layer.id as LayerId] = layer.enabled
      }
    }
    return map
  }, [guardLayers])

  return (
    <div className="viz-canvas">
      <Canvas
        dpr={[1, 1.75]}
        camera={{ position: [4.2, 2.8, 5.4], fov: 40 }}
        gl={{ antialias: true, alpha: false }}
      >
        <Scene
          enabledMap={enabledMap}
          events={events}
          selected={selected}
          onSelect={onSelect}
        />
      </Canvas>
    </div>
  )
}

export { LAYER_META, LAYER_ORDER }
