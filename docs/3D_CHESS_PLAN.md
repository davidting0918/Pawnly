# 🏰 Pawnly 3D Chess Board — Full Implementation Plan

## Overview

Add a fully interactive 3D chess board as a switchable theme alongside the existing 2D boards. Users can pick "3D Wizard" or "3D Marble" from the same theme picker. The 3D board is lazy-loaded so it doesn't affect load times for 2D users.

---

## Phase 1: Foundation (3D Board + Geometric Pieces)

### Goal
Get a working 3D chess board with simple geometric pieces, fully integrated with the existing game logic (WebSocket, chess.js, turns, etc.)

### 1.1 New Dependencies

```bash
npm install three @types/three @react-three/fiber@9 @react-three/drei
```

| Package | Purpose | Size (gzipped) |
|---------|---------|----------------|
| `three` | 3D engine | ~150KB |
| `@react-three/fiber@9` | React renderer for Three.js (React 19 compatible) | ~40KB |
| `@react-three/drei` | Helpers: OrbitControls, Environment, shadows, etc. | ~30KB |

### 1.2 File Structure

```
frontend/src/
├── components/
│   ├── Board3D/
│   │   ├── Board3D.tsx          # Main 3D board component
│   │   ├── Board3DWrapper.tsx   # Lazy-loading wrapper (React.lazy)
│   │   ├── ChessSquare3D.tsx    # Single 3D square (clickable, highlightable)
│   │   ├── ChessPiece3D.tsx     # Single piece (geometric or glTF model)
│   │   ├── PieceModels.tsx      # glTF model loader + cache
│   │   ├── MoveAnimation.tsx    # Piece movement animation controller
│   │   ├── CaptureEffect3D.tsx  # Destruction/explosion on capture
│   │   ├── BoardLighting.tsx    # Lights, shadows, environment
│   │   └── CameraController.tsx # OrbitControls + auto-rotate for black
│   ├── BoardThemePicker.tsx     # Updated: add 3D themes
│   └── ExperimentalEffects...   # Existing 2D FX (unchanged)
├── themes/
│   └── boardThemes.ts           # Updated: add 3D theme entries
├── models/                      # glTF/glb model files (Phase 2)
│   ├── wizard/                  # Wizard chess style
│   │   ├── king_w.glb
│   │   ├── king_b.glb
│   │   └── ... (12 files)
│   └── marble/                  # Marble style
│       └── ...
```

### 1.3 Theme System Update

```typescript
// boardThemes.ts — extended interface
export interface BoardTheme {
  id: string;
  name: string;
  description: string;
  preview: string;
  type: '2d' | '3d';          // NEW: board type
  
  // 2D-specific (existing)
  darkSquare?: CSSProperties;
  lightSquare?: CSSProperties;
  boardBorder?: string;
  effects?: boolean;
  experimental?: boolean;
  
  // 3D-specific (new)
  modelSet?: string;           // 'geometric' | 'wizard' | 'marble'
  boardMaterial?: string;      // 'stone' | 'marble' | 'wood' | 'obsidian'
  lightingPreset?: string;     // 'castle' | 'bright' | 'dramatic'
  pieceStyle?: {
    white: { color: string; emissive?: string; metalness?: number; roughness?: number };
    black: { color: string; emissive?: string; metalness?: number; roughness?: number };
  };
}

// New 3D themes
{
  id: 'wizard',
  name: '🏰 Wizard Chess',
  description: 'Harry Potter style stone pieces',
  type: '3d',
  modelSet: 'wizard',        // Phase 2: glTF models
  boardMaterial: 'stone',
  lightingPreset: 'castle',  // Warm torchlight, dark ambient
  pieceStyle: {
    white: { color: '#d4c5a9', metalness: 0.1, roughness: 0.8 },  // Sandstone
    black: { color: '#2d2d2d', metalness: 0.1, roughness: 0.7 },  // Dark stone
  },
},
{
  id: 'marble',
  name: '🏛️ 3D Marble',
  description: 'Elegant marble board',
  type: '3d',
  modelSet: 'geometric',     // Phase 1: geometric shapes
  boardMaterial: 'marble',
  lightingPreset: 'bright',
  pieceStyle: {
    white: { color: '#f0f0f0', metalness: 0.3, roughness: 0.2 },
    black: { color: '#1a1a2e', metalness: 0.3, roughness: 0.2 },
  },
}
```

### 1.4 Board3D Component (Core)

```tsx
// Board3D.tsx — simplified structure
<Canvas shadows camera={{ position: [0, 8, 6], fov: 45 }}>
  {/* Lighting */}
  <BoardLighting preset={theme.lightingPreset} />
  
  {/* Controls — orbit around board, clamped angles */}
  <CameraController orientation={boardOrientation} />
  
  {/* Board */}
  <group>
    {/* 64 squares */}
    {squares.map(sq => (
      <ChessSquare3D
        key={sq.id}
        position={[col, 0, row]}
        isLight={(col + row) % 2 === 0}
        isHighlighted={highlights[sq.id]}
        isSelected={selectedSquare === sq.id}
        onClick={() => handleSquareClick(sq.id)}
        material={theme.boardMaterial}
      />
    ))}
    
    {/* Board frame/border */}
    <BoardFrame material={theme.boardMaterial} />
  </group>
  
  {/* Pieces */}
  {pieces.map(piece => (
    <ChessPiece3D
      key={piece.id}
      type={piece.type}        // 'K','Q','R','B','N','P'
      color={piece.color}      // 'w' | 'b'
      position={piece.position} // [x, y, z]
      isAnimating={piece.animating}
      targetPosition={piece.target}
      style={theme.pieceStyle[piece.color === 'w' ? 'white' : 'black']}
      modelSet={theme.modelSet}
      onClick={() => handlePieceClick(piece)}
    />
  ))}
  
  {/* Capture effects */}
  <CaptureEffect3D captures={pendingCaptures} />
  
  {/* Environment */}
  <Environment preset={theme.lightingPreset === 'castle' ? 'night' : 'studio'} />
  <ContactShadows position={[0, -0.01, 0]} />
</Canvas>
```

### 1.5 Interaction Flow

```
User clicks piece
  → Highlight legal moves (squares glow green)
  → User clicks target square
  → Send WS move (same as 2D: { type: 'move', from, to })
  → Receive WS update
  → Animate piece sliding from source to target
  → If capture: play destruction animation on captured piece
  → Update board state
```

**Key difference from 2D:** No drag-and-drop in 3D (too complex with raycasting). Use **click-to-select, click-to-move** instead.

### 1.6 Geometric Pieces (Phase 1 Placeholder)

Simple Three.js geometry until we have glTF models:

| Piece | Shape |
|-------|-------|
| King ♔ | Cylinder + Cross on top |
| Queen ♕ | Cylinder + Sphere + Crown ring |
| Rook ♖ | Cylinder + Box (castle tower) |
| Bishop ♗ | Cylinder + Cone (pointed hat) |
| Knight ♘ | Cylinder + Tilted cone (horse-ish) |
| Pawn ♙ | Cylinder + Small sphere |

Each piece: ~20 lines of JSX. Temporary but fully playable.

### 1.7 Camera Controller

```typescript
// Auto-position based on player side
const CameraController = ({ orientation }) => {
  const { camera } = useThree();
  
  useEffect(() => {
    const target = orientation === 'white'
      ? [0, 8, 6]    // Looking from white's perspective
      : [0, 8, -6];  // Looking from black's perspective
    
    // Smooth transition
    gsap.to(camera.position, { ...target, duration: 1 });
  }, [orientation]);
  
  return <OrbitControls 
    maxPolarAngle={Math.PI / 2.5}  // Don't go below board
    minPolarAngle={Math.PI / 6}     // Don't go too overhead
    enablePan={false}                // No panning
    minDistance={6}
    maxDistance={14}
  />;
};
```

### 1.8 Game.tsx Integration

```tsx
// Game.tsx — conditional rendering
const is3D = boardTheme.type === '3d';

{is3D ? (
  <Board3DWrapper
    fen={game.fen()}
    orientation={boardOrientation}
    theme={boardTheme}
    onMove={(from, to) => {
      // Same WS send logic as 2D onDrop
      ws.current.send(JSON.stringify({ type: 'move', from, to }));
    }}
    isMyTurn={isMyTurn}
    lastMove={lastMoveSquares}
    isCheck={game.isCheck()}
    gameOver={phase === 'finished'}
  />
) : (
  // Existing 2D Chessboard (unchanged)
  <Chessboard options={{...}} />
)}
```

### 1.9 Lazy Loading

```tsx
// Board3DWrapper.tsx
const Board3D = React.lazy(() => import('./Board3D'));

export const Board3DWrapper = (props) => (
  <Suspense fallback={
    <div className="aspect-square bg-zinc-900 rounded-2xl flex items-center justify-center">
      <span className="animate-spin ...">Loading 3D...</span>
    </div>
  }>
    <Board3D {...props} />
  </Suspense>
);
```

Three.js chunk (~220KB gzipped) only loads when user selects a 3D theme.

---

## Phase 2: Wizard Chess Models (Sketchfab)

### Goal
Replace geometric pieces with real 3D models from Sketchfab.

### 2.1 Model Requirements

**Need 6 unique piece models × 2 colors = 12 files (or 6 + recolor)**

Search on Sketchfab:
- "medieval chess set" — stone/gothic style
- "chess pieces low poly" — for performance
- "wizard chess" — Harry Potter inspired

**Ideal model specs:**
- Format: glTF 2.0 / .glb (preferred for web)
- Poly count: <5K triangles per piece (for performance)
- License: CC-BY or purchasable
- Style: Stone/medieval/Gothic — NOT modern/minimalist

**Color handling:** Download one color (white), duplicate, change material color for black. Saves file size.

### 2.2 Model Pipeline

```
Sketchfab download (.glb)
  → Blender: clean up, reduce polys, center origin, normalize scale
  → gltf-pipeline: compress (Draco compression, -50% size)
  → gltfjsx (https://gltf.pmnd.rs/): auto-generate React component
  → Place in /public/models/wizard/
```

Tools:
```bash
# Convert & compress
npx gltf-pipeline -i king.glb -o king_compressed.glb --draco.compressionLevel 7

# Auto-generate React component from model
npx gltfjsx king_compressed.glb --types --transform
```

### 2.3 Model Loader

```tsx
// PieceModels.tsx
import { useGLTF } from '@react-three/drei';

// Preload all models when 3D theme is selected
const MODEL_PATHS = {
  wizard: {
    K: '/models/wizard/king.glb',
    Q: '/models/wizard/queen.glb',
    R: '/models/wizard/rook.glb',
    B: '/models/wizard/bishop.glb',
    N: '/models/wizard/knight.glb',
    P: '/models/wizard/pawn.glb',
  }
};

export function preloadModels(set: string) {
  Object.values(MODEL_PATHS[set]).forEach(useGLTF.preload);
}

export function PieceModel({ type, color, style }) {
  const { scene } = useGLTF(MODEL_PATHS[theme.modelSet][type]);
  const cloned = scene.clone(); // Each instance needs its own clone
  
  // Apply color based on side
  cloned.traverse(child => {
    if (child.isMesh) {
      child.material = new MeshStandardMaterial({
        color: style.color,
        metalness: style.metalness,
        roughness: style.roughness,
      });
      child.castShadow = true;
    }
  });
  
  return <primitive object={cloned} />;
}
```

### 2.4 Sketchfab Shopping List

Recommended free/affordable sets:

1. **Gothic Chess Set** — dark stone, ornate
   - Search: "gothic chess set glb"
   - Style: Cathedral/gargoyle aesthetic

2. **Medieval Chess Set** — classic stone warriors
   - Search: "medieval chess pieces"
   - Style: Knights on horses, castle rooks, bishop with staff

3. **Fantasy Chess Set** — wizard/magical
   - Search: "fantasy chess set"
   - Style: Wizards, dragons, magical creatures

**Budget option:** Buy one set ($10-30), recolor for multiple themes.

---

## Phase 3: Animations & Effects

### 3.1 Piece Movement Animation

```tsx
// MoveAnimation.tsx
import { useSpring, animated } from '@react-spring/three';

function AnimatedPiece({ from, to, children }) {
  const { position } = useSpring({
    position: to,
    from: { position: from },
    config: { tension: 120, friction: 14 },  // Smooth spring
  });
  
  return (
    <animated.group position={position}>
      {children}
    </animated.group>
  );
}
```

**Special movements:**
| Move | Animation |
|------|-----------|
| Normal slide | Linear interpolation A→B, 0.5s |
| Knight jump | Arc path (bezier curve), higher Y midpoint |
| Castling | King + Rook move simultaneously |
| Capture | Attacker slides → captured piece shatters |
| Promotion | Pawn reaches end → shrink → queen model grows |

### 3.2 Capture Destruction (巫師棋核心！)

**Option A: Pre-fractured models (recommended)**
- In Blender: use Cell Fracture addon to break each piece into 8-15 fragments
- Export fragments as separate meshes in the same .glb
- On capture: hide original → show fragments → apply physics (gravity + outward force)

**Option B: Runtime shattering**
```bash
npm install three-fracture  # or custom implementation
```
- More flexible but heavier on GPU

**Option C: Particle replacement (simplest)**
- On capture: hide piece → spawn 20-30 small boxes at piece position
- Apply random velocity + gravity + spin
- Fade out over 1.5s

### 3.3 Lighting Presets

```typescript
const LIGHTING_PRESETS = {
  castle: {
    // Harry Potter great hall vibe
    ambient: { color: '#1a0f00', intensity: 0.3 },
    directional: { color: '#ff9944', intensity: 0.8, position: [5, 10, 5] },
    points: [
      // Torch-like point lights on corners
      { color: '#ff6600', intensity: 2, position: [-4, 3, -4], distance: 8 },
      { color: '#ff6600', intensity: 2, position: [4, 3, 4], distance: 8 },
    ],
    fog: { color: '#0a0a0a', near: 10, far: 25 },
    shadows: true,
  },
  bright: {
    // Clean studio lighting
    ambient: { color: '#ffffff', intensity: 0.6 },
    directional: { color: '#ffffff', intensity: 1, position: [5, 10, 5] },
    points: [],
    fog: null,
    shadows: true,
  },
  dramatic: {
    // High contrast, single strong light
    ambient: { color: '#111', intensity: 0.2 },
    directional: { color: '#ffeedd', intensity: 1.5, position: [3, 8, 2] },
    points: [],
    fog: { color: '#000', near: 12, far: 20 },
    shadows: true,
  },
};
```

### 3.4 Post-Processing (optional, Phase 3+)

```bash
npm install @react-three/postprocessing
```

```tsx
import { EffectComposer, Bloom, SSAO } from '@react-three/postprocessing';

<EffectComposer>
  <Bloom luminanceThreshold={0.8} intensity={0.5} />  {/* Glow on emissive */}
  <SSAO radius={0.1} intensity={15} />                 {/* Ambient occlusion */}
</EffectComposer>
```

---

## Phase 4: Polish & Extra Features

### 4.1 Board Ambiance
- Dust particles floating in the air (drei `Sparkles`)
- Torch flame particles on corner pillars
- Fog/mist at board level

### 4.2 Sound Effects (optional)
- Piece slide: stone grinding sound
- Capture: stone crumbling/breaking
- Check: dramatic horn/bell
- Ambient: castle background noise

### 4.3 Piece Idle Animations
- Subtle breathing (sin wave Y offset)
- Knight's horse occasionally shakes head
- King's crown slight wobble

### 4.4 Performance Optimization
- `InstancedMesh` for pawns (8 instances, 1 draw call)
- LOD (Level of Detail): lower poly at distance
- Frustum culling (automatic in R3F)
- `<Bvh>` from drei for faster raycasting
- Target: 60fps on mid-range phone

---

## Implementation Timeline

| Phase | Scope | Estimated Time | Deliverable |
|-------|-------|---------------|-------------|
| **1a** | R3F setup + geometric pieces + click interaction | 1 day | Playable 3D board |
| **1b** | Theme picker integration + lazy loading | 0.5 day | Switch 2D↔3D |
| **1c** | Slide animations + camera controller | 0.5 day | Smooth UX |
| **2a** | Find & download Sketchfab models | 0.5 day | .glb files ready |
| **2b** | Model pipeline + loader component | 0.5 day | Real chess pieces |
| **2c** | Wizard theme lighting + ambiance | 0.5 day | Castle atmosphere |
| **3a** | Capture destruction animation | 1 day | Pieces shatter! |
| **3b** | Special move animations (knight arc, castling) | 0.5 day | Polish |
| **3c** | Post-processing (Bloom, SSAO) | 0.5 day | Visual quality |
| **4** | Particles, sounds, idle anims | 1 day | Full polish |

**Total: ~6-7 days of work**

Phase 1 alone gives you a fully playable 3D board. Each subsequent phase adds visual quality.

---

## Technical Risk & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Three.js bundle too large | Slow first load | Code-splitting (lazy load 3D chunk) |
| Mobile GPU can't handle it | Laggy on phones | Quality settings toggle (shadows on/off, post-processing off) |
| Sketchfab models too heavy | Long download | Draco compression, LOD, progressive loading |
| Click detection unreliable | Misclicks | Large invisible click targets per square, highlight on hover |
| R3F v9 + React 19 compatibility | Build errors | Already verified: v9.5.0 supports React 19 |

---

## Summary

```
User opens Game → picks "🏰 Wizard Chess" theme → lazy-loads Three.js
→ 3D stone board appears → camera auto-positions for their side
→ Click piece → legal squares glow → click target → piece slides
→ Capture? → captured piece SHATTERS → fragments scatter
→ Castle lighting, fog, dust particles floating
→ All game logic unchanged (same WS, same chess.js)
```
