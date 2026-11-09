import { Html, OrbitControls, Text } from '@react-three/drei'
import { Canvas, useFrame } from '@react-three/fiber'
import { useMemo, useRef } from 'react'
import type { Group, Mesh } from 'three'
import type { GuardEventTrace, GuardLayerInfo } from '../api'

export type LayerId = 'user_input' | 'retrieved_context' | 'tool_output'

type LayerVisual = {
  id: LayerId
  label: string
  y: number
  enabled: boolean
}

const LAYER_ORDER: LayerId[] = ['user_input', 'retrieved_context', 'tool_output']

type LayerStatus = 'idle' | 'allow' | 'block' | 'drop' | 'flag'

function layerStatus(layerId: LayerId, events: GuardEventTrace[]): LayerStatus {
  const matches = events.filter((event) => event.layer === layerId)
  if (matches.length === 0) return 'idle'
  if (matches.some((event) => event.action === 'block')) return 'block'
  if (matches.some((event) => event.action === 'drop')) return 'drop'
  if (matches.some((event) => event.action === 'flag')) return 'flag'
  return 'allow'
}

function statusColor(status: LayerStatus, enabled: boolean): string {
  if (!enabled) return '#9aa6b5'
  switch (status) {
    case 'block':
    case 'drop':
      return '#c2410c'
    case 'flag':
      return '#b45309'
    case 'allow':
      return '#0b7f8a'
    default:
      return '#4b5a6d'
  }
}

function GuardCore({ active }: { active: boolean }) {
  const ref = useRef<Mesh>(null)
  useFrame((_, delta) => {
    if (!ref.current) return
    ref.current.rotation.y += delta * (active ? 1.4 : 0.35)
    ref.current.rotation.x += delta * (active ? 0.5 : 0.12)
  })

  return (
    <mesh ref={ref} position={[0, 0.15, 0]}>
      <icosahedronGeometry args={[0.55, 1]} />
      <meshStandardMaterial
        color={active ? '#0b7f8a' : '#6b7c90'}
        emissive={active ? '#066069' : '#1f2933'}
        emissiveIntensity={active ? 0.55 : 0.15}
        metalness={0.35}
        roughness={0.25}
        transparent
        opacity={0.92}
      />
    </mesh>
  )
}

function LayerPlane({
  layer,
  status,
  selected,
  onSelect,
}: {
  layer: LayerVisual
  status: LayerStatus
  selected: boolean
  onSelect: (id: LayerId) => void
}) {
  const color = statusColor(status, layer.enabled)
  const group = useRef<Group>(null)

  useFrame((state) => {
    if (!group.current) return
    const pulse = status === 'idle' ? 0 : Math.sin(state.clock.elapsedTime * 3) * 0.025
    group.current.position.y = layer.y + pulse
  })

  return (
    <group
      ref={group}
      position={[0, layer.y, 0]}
      onClick={(event) => {
        event.stopPropagation()
        onSelect(layer.id)
      }}
      onPointerOver={() => {
        document.body.style.cursor = 'pointer'
      }}
      onPointerOut={() => {
        document.body.style.cursor = 'default'
      }}
    >
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[4.8, 2.35]} />
        <meshStandardMaterial
          color={color}
          transparent
          opacity={selected ? 0.4 : layer.enabled ? 0.26 : 0.12}
          metalness={0.08}
          roughness={0.5}
          side={2}
        />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.015, 0]}>
        <ringGeometry args={[0.9, 1.02, 64]} />
        <meshBasicMaterial color={color} transparent opacity={selected ? 0.95 : 0.4} />
      </mesh>
      <Text
        position={[-1.85, 0.06, 0.75]}
        rotation={[-Math.PI / 2.35, 0, 0]}
        fontSize={0.2}
        color="#12161c"
        anchorX="left"
        anchorY="middle"
        maxWidth={2.5}
      >
        {`${layer.label}${layer.enabled ? '' : ' (off)'}`}
      </Text>
      <Html position={[1.75, 0.1, 0.6]} center style={{ pointerEvents: 'none' }}>
        <div className={`viz-chip ${status}`}>{status}</div>
      </Html>
    </group>
  )
}

function SceneContent({
  layers,
  events,
  selected,
  onSelect,
}: {
  layers: LayerVisual[]
  events: GuardEventTrace[]
  selected: LayerId | null
  onSelect: (id: LayerId) => void
}) {
  const active = events.some((event) => event.injection)

  return (
    <>
      <color attach="background" args={['#d9e2ea']} />
      <ambientLight intensity={0.85} />
      <directionalLight position={[4, 8, 3]} intensity={1.15} />
      <directionalLight position={[-3, 2, -4]} intensity={0.35} />

      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.55, 0]}>
        <circleGeometry args={[3.4, 64]} />
        <meshStandardMaterial color="#c5d0db" transparent opacity={0.55} />
      </mesh>

      {layers.map((layer) => (
        <LayerPlane
          key={layer.id}
          layer={layer}
          status={layerStatus(layer.id, events)}
          selected={selected === layer.id}
          onSelect={onSelect}
        />
      ))}

      <GuardCore active={active} />
      <Text
        position={[0, 1.05, 0]}
        fontSize={0.16}
        color="#066069"
        anchorX="center"
        anchorY="middle"
      >
        Decision model
      </Text>

      <OrbitControls
        enablePan={false}
        minDistance={4}
        maxDistance={11}
        maxPolarAngle={Math.PI / 2.05}
        target={[0, 0, 0]}
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
  const layers = useMemo<LayerVisual[]>(() => {
    const byId = new Map(guardLayers.map((layer) => [layer.id, layer]))
    return LAYER_ORDER.map((id, index) => {
      const meta = byId.get(id)
      return {
        id,
        label: meta?.label ?? id,
        enabled: meta?.enabled ?? true,
        y: 1.05 - index * 0.95,
      }
    })
  }, [guardLayers])

  return (
    <div className="viz-canvas">
      <Canvas camera={{ position: [3.8, 3.2, 5.2], fov: 42 }}>
        <SceneContent
          layers={layers}
          events={events}
          selected={selected}
          onSelect={onSelect}
        />
      </Canvas>
    </div>
  )
}
