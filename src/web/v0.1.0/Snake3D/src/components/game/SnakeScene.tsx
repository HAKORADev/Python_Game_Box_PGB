'use client';

import React, { useRef, useMemo, useEffect, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { useGameStore } from '@/game/store';
import { gridToWorld, Position, OpenSides, hasAnyOpenSide, getGameHour, getDaylight, getSunPosition, getMoonPosition, smoothstep, TimeMode, ShadowMode, LampColorMode, PowerUpType, POWERUP_EXPIRY } from '@/game/constants';
import dynamic from 'next/dynamic';

const PathTracer = dynamic(() => import('./PathTracer'), { ssr: false });

function ShadowSetup() {
  const setState = useThree((state) => state.set);
  useEffect(() => {
    setState((prev) => {
      prev.gl.shadowMap.type = THREE.PCFSoftShadowMap;
      prev.gl.shadowMap.needsUpdate = true;
      return prev;
    });
  }, [setState]);
  return null;
}

function DynamicExposure() {
  const { gl } = useThree();
  useFrame((state) => {
    const elapsed = state.clock.elapsedTime;
    const hour = getGameHour(elapsed);
    const daylight = getDaylight(hour);
    
    
    const targetExposure = 0.6 + daylight * 0.4;
    gl.toneMappingExposure = targetExposure;
  });
  return null;
}

function Ground() {
  const gridSize = useGameStore(s => s.gridSize);
  const texture = useMemo(() => {
    const size = 512;
    const canvas = document.createElement('canvas');
    canvas.width = size; canvas.height = size;
    const ctx = canvas.getContext('2d')!;
    ctx.fillStyle = '#3a7d2c';
    ctx.fillRect(0, 0, size, size);
    const cellSize = size / 24;
    for (let x = 0; x < 24; x++) {
      for (let z = 0; z < 24; z++) {
        const isEven = (x + z) % 2 === 0;
        ctx.fillStyle = isEven ? '#3d8230' : '#357828';
        ctx.fillRect(x * cellSize, z * cellSize, cellSize, cellSize);
        for (let i = 0; i < 6; i++) {
          const nx = x * cellSize + Math.random() * cellSize;
          const ny = z * cellSize + Math.random() * cellSize;
          ctx.fillStyle = `rgba(${50 + Math.random() * 30}, ${110 + Math.random() * 40}, ${30 + Math.random() * 20}, 0.3)`;
          ctx.fillRect(nx, ny, 2 + Math.random() * 4, 1 + Math.random() * 3);
        }
      }
    }
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.06)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 24; i++) {
      ctx.beginPath(); ctx.moveTo(i * cellSize, 0); ctx.lineTo(i * cellSize, size); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, i * cellSize); ctx.lineTo(size, i * cellSize); ctx.stroke();
    }
    const tex = new THREE.CanvasTexture(canvas);
    tex.wrapS = tex.wrapT = THREE.ClampToEdgeWrapping;
    tex.magFilter = THREE.LinearFilter;
    tex.minFilter = THREE.LinearMipmapLinearFilter;
    return tex;
  }, []);

  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} receiveShadow castShadow>
      <planeGeometry args={[gridSize, gridSize]} />
      <meshPhysicalMaterial
        map={texture}
        roughness={0.85}
        metalness={0.02}
        clearcoat={0.05}
        clearcoatRoughness={0.8}
        envMapIntensity={0.3}
      />
    </mesh>
  );
}

function BorderWalls() {
  const gridSize = useGameStore(s => s.gridSize);
  const openSides = useGameStore(s => s.openSides);
  const half = gridSize / 2;
  const wallHeight = 0.6;
  const wallThickness = 0.3;

  
  const wallMaterial = useMemo(() => new THREE.MeshPhysicalMaterial({
    color: '#5a3a1a',
    roughness: 0.75,
    metalness: 0.05,
    clearcoat: 0.02,
    clearcoatRoughness: 0.9,
  }), []);
  const glowMaterial = useMemo(() => new THREE.MeshPhysicalMaterial({
    color: '#60d9fa',
    emissive: '#60d9fa',
    emissiveIntensity: 0.6,
    transparent: true,
    opacity: 0.5,
    roughness: 0.1,
    metalness: 0.8,
  }), []);

  const glowEdges: { pos: [number, number, number]; scale: [number, number, number] }[] = [];
  const wallSides: { pos: [number, number, number]; size: [number, number, number] }[] = [];

  if (openSides.top) glowEdges.push({ pos: [0, 0.05, -half], scale: [gridSize, 0.1, 0.05] });
  else wallSides.push({ pos: [0, wallHeight / 2, -half - wallThickness / 2], size: [gridSize + wallThickness * 2, wallHeight, wallThickness] });
  if (openSides.bottom) glowEdges.push({ pos: [0, 0.05, half], scale: [gridSize, 0.1, 0.05] });
  else wallSides.push({ pos: [0, wallHeight / 2, half + wallThickness / 2], size: [gridSize + wallThickness * 2, wallHeight, wallThickness] });
  if (openSides.left) glowEdges.push({ pos: [-half, 0.05, 0], scale: [0.05, 0.1, gridSize] });
  else wallSides.push({ pos: [-half - wallThickness / 2, wallHeight / 2, 0], size: [wallThickness, wallHeight, gridSize + wallThickness * 2] });
  if (openSides.right) glowEdges.push({ pos: [half, 0.05, 0], scale: [0.05, 0.1, gridSize] });
  else wallSides.push({ pos: [half + wallThickness / 2, wallHeight / 2, 0], size: [wallThickness, wallHeight, gridSize + wallThickness * 2] });

  return (
    <group>
      {wallSides.map((w, i) => (
        <mesh key={`bw-${i}`} position={w.pos} receiveShadow castShadow material={wallMaterial}>
          <boxGeometry args={w.size} />
        </mesh>
      ))}
      {glowEdges.map((e, i) => (
        <mesh key={`ge-${i}`} position={e.pos} scale={e.scale} material={glowMaterial}>
          <boxGeometry args={[1, 1, 1]} />
        </mesh>
      ))}
    </group>
  );
}

function InteriorWalls() {
  const mapConfig = useGameStore(s => s.mapConfig);
  const gridSize = useGameStore(s => s.gridSize);
  const wallMaterial = useMemo(() => new THREE.MeshPhysicalMaterial({
    color: '#6b7280',
    roughness: 0.7,
    metalness: 0.1,
    clearcoat: 0.03,
    clearcoatRoughness: 0.85,
  }), []);
  if (!mapConfig || mapConfig.walls.length === 0) return null;
  return (
    <group>
      {mapConfig.walls.map((wall, i) => {
        const [wx, , wz] = gridToWorld(wall.x, wall.z, gridSize);
        return (
          <mesh key={`iw-${i}`} position={[wx, 0.35, wz]} castShadow receiveShadow material={wallMaterial}>
            <boxGeometry args={[0.96, 0.7, 0.96]} />
          </mesh>
        );
      })}
    </group>
  );
}

interface SnakeSegmentGeo { geometry: THREE.BufferGeometry; startT: number; endT: number }

function buildSnakeSegments(
  smoothPositions: THREE.Vector3[], gridSize: number,
  headColorHex: string, tailColorHex: string, bodyRadius: number
): SnakeSegmentGeo[] {
  if (smoothPositions.length < 2) return [];
  const segments: { positions: THREE.Vector3[]; startIdx: number; endIdx: number }[] = [];
  let current: THREE.Vector3[] = [smoothPositions[0].clone()];
  let segStart = 0;
  for (let i = 1; i < smoothPositions.length; i++) {
    const prev = smoothPositions[i - 1]; const curr = smoothPositions[i];
    if (Math.abs(curr.x - prev.x) > gridSize * 0.4 || Math.abs(curr.z - prev.z) > gridSize * 0.4) {
      if (current.length >= 2) segments.push({ positions: current, startIdx: segStart, endIdx: i - 1 });
      current = [curr.clone()]; segStart = i;
    } else { current.push(curr.clone()); }
  }
  if (current.length >= 2) segments.push({ positions: current, startIdx: segStart, endIdx: smoothPositions.length - 1 });
  const totalLen = smoothPositions.length;
  const headColor = new THREE.Color(headColorHex); const tailColor = new THREE.Color(tailColorHex);
  return segments.map(seg => {
    const curve = new THREE.CatmullRomCurve3(seg.positions, false, 'catmullrom', 0.25);
    const tubularSegs = Math.max(8, seg.positions.length * 8);
    const radialSegs = 10;
    const geo = new THREE.TubeGeometry(curve, tubularSegs, bodyRadius, radialSegs, false);
    const posAttr = geo.getAttribute('position');
    const ringCount = tubularSegs + 1; const totalVerts = posAttr.count;
    const vertsPerRing = Math.round(totalVerts / ringCount);
    const segStartT = seg.startIdx / Math.max(1, totalLen - 1);
    const segEndT = seg.endIdx / Math.max(1, totalLen - 1);
    const colors = new Float32Array(totalVerts * 3);
    for (let ring = 0; ring < ringCount; ring++) {
      const localT = ring / Math.max(1, ringCount - 1);
      const globalT = segStartT + (segEndT - segStartT) * localT;
      const taperScale = 1.0 - globalT * 0.55;
      const color = headColor.clone().lerp(tailColor, globalT);
      const center = curve.getPointAt(Math.min(localT, 0.999));
      for (let v = 0; v < vertsPerRing; v++) {
        const idx = ring * vertsPerRing + v;
        if (idx >= totalVerts) break;
        posAttr.setX(idx, center.x + (posAttr.getX(idx) - center.x) * taperScale);
        posAttr.setY(idx, center.y + (posAttr.getY(idx) - center.y) * taperScale);
        posAttr.setZ(idx, center.z + (posAttr.getZ(idx) - center.z) * taperScale);
        colors[idx * 3] = color.r; colors[idx * 3 + 1] = color.g; colors[idx * 3 + 2] = color.b;
      }
    }
    posAttr.needsUpdate = true;
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geo.computeVertexNormals();
    return { geometry: geo, startT: segStartT, endT: segEndT };
  });
}

function Snake() {
  const snake = useGameStore(s => s.snake);
  const prevSnake = useGameStore(s => s.prevSnake);
  const direction = useGameStore(s => s.direction);
  const gridSize = useGameStore(s => s.gridSize);
  const baseSpeed = useGameStore(s => s.baseSpeed);
  const speedBoostEnd = useGameStore(s => s.speedBoostEnd);
  const slowEnd = useGameStore(s => s.slowEnd);
  const lastPlayerMoveTime = useGameStore(s => s.lastPlayerMoveTime);
  const immortalEnd = useGameStore(s => s.immortalEnd);
  const headRef = useRef<THREE.Group>(null);
  const bodyGroupRef = useRef<THREE.Group>(null);
  const tongueTimerRef = useRef(0);
  const [tongueOut, setTongueOut] = useState(false);
  const smoothPositions = useRef<THREE.Vector3[]>(
    snake.map(seg => { const [wx, , wz] = gridToWorld(seg.x, seg.z, gridSize); return new THREE.Vector3(wx, 0.35, wz); })
  );
  
  const lastBuildKey = useRef<string>('');
  const bodyMaterial = useMemo(() => new THREE.MeshPhysicalMaterial({
    color: '#3dba6a',
    roughness: 0.3,
    metalness: 0.1,
    clearcoat: 0.4,
    clearcoatRoughness: 0.3,
    emissive: '#1a5c2a',
    emissiveIntensity: 0.15,
    vertexColors: true,
    envMapIntensity: 0.6,
    transparent: true,
    opacity: 1,
  }), []);
  const eyeOffsets = useMemo(() => {
    const dist = 0.14, fwd = 0.28, up = 0.25;
    return {
      UP: { l: [-dist, up, -fwd] as [number,number,number], r: [dist, up, -fwd] as [number,number,number] },
      DOWN: { l: [-dist, up, fwd] as [number,number,number], r: [dist, up, fwd] as [number,number,number] },
      LEFT: { l: [-fwd, up, -dist] as [number,number,number], r: [-fwd, up, dist] as [number,number,number] },
      RIGHT: { l: [fwd, up, -dist] as [number,number,number], r: [fwd, up, dist] as [number,number,number] },
    };
  }, []);

  useFrame((_, delta) => {
    const dt = Math.min(delta, 0.1);

    
    const now = Date.now();
    
    const playerHasBoost = speedBoostEnd > 0 && now < speedBoostEnd;
    const playerIsSlowed = slowEnd > 0 && now < slowEnd;
    let playerInterval = baseSpeed;
    if (playerHasBoost) playerInterval /= 2;
    if (playerIsSlowed) playerInterval *= 2;
    const elapsed = now - lastPlayerMoveTime;
    
    
    const rawT = playerInterval > 0 ? Math.min(elapsed / playerInterval, 1.0) : 1.0;
    
    const t = rawT * rawT * (3 - 2 * rawT);

    
    const len = snake.length;
    const prevLen = prevSnake.length;

    
    while (smoothPositions.current.length < len) {
      const last = smoothPositions.current[smoothPositions.current.length - 1] || new THREE.Vector3();
      smoothPositions.current.push(last.clone());
    }
    const lengthDecreased = len < smoothPositions.current.length;
    if (lengthDecreased) {
      smoothPositions.current.length = len;
    }

    for (let i = 0; i < len; i++) {
      const [curX, , curZ] = gridToWorld(snake[i].x, snake[i].z, gridSize);
      const curTarget = new THREE.Vector3(curX, 0.35, curZ);

      
      if (i < prevLen && !lengthDecreased) {
        const [prevX, , prevZ] = gridToWorld(prevSnake[i].x, prevSnake[i].z, gridSize);
        const prevTarget = new THREE.Vector3(prevX, 0.35, prevZ);

        
        if (Math.abs(curX - prevX) > gridSize * 0.4 || Math.abs(curZ - prevZ) > gridSize * 0.4) {
          
          smoothPositions.current[i].copy(curTarget);
        } else {
          
          smoothPositions.current[i].lerpVectors(prevTarget, curTarget, t);
        }
      } else {
        
        smoothPositions.current[i].copy(curTarget);
      }
    }

    if (bodyGroupRef.current && smoothPositions.current.length >= 2) {
      
      const posKey = smoothPositions.current.map(p => `${p.x.toFixed(2)},${p.z.toFixed(2)}`).join('|');
      if (posKey !== lastBuildKey.current) {
        lastBuildKey.current = posKey;
        const segments = buildSnakeSegments(smoothPositions.current, gridSize, '#4ade80', '#166534', 0.26);
        while (bodyGroupRef.current.children.length > segments.length) { const c = bodyGroupRef.current.children[bodyGroupRef.current.children.length - 1]; if ((c as THREE.Mesh).geometry) (c as THREE.Mesh).geometry.dispose(); bodyGroupRef.current.remove(c); }
        for (let i = 0; i < segments.length; i++) {
          if (i < bodyGroupRef.current.children.length) { const m = bodyGroupRef.current.children[i] as THREE.Mesh; (m).geometry.dispose(); (m).geometry = segments[i].geometry; }
          else { const m = new THREE.Mesh(segments[i].geometry, bodyMaterial); m.castShadow = true; m.receiveShadow = true; bodyGroupRef.current.add(m); }
        }
      }
    } else if (bodyGroupRef.current && smoothPositions.current.length < 2) {
      while (bodyGroupRef.current.children.length > 0) { const c = bodyGroupRef.current.children[0]; if ((c as THREE.Mesh).geometry) (c as THREE.Mesh).geometry.dispose(); bodyGroupRef.current.remove(c); }
      lastBuildKey.current = '';
    }
    if (headRef.current && smoothPositions.current.length > 0) { const hp = smoothPositions.current[0]; headRef.current.position.set(hp.x, 0.42, hp.z); }
    tongueTimerRef.current += dt; if (tongueTimerRef.current > 2.5) { setTongueOut(prev => !prev); tongueTimerRef.current = 0; }

    
    const isGhost = immortalEnd > 0 && Date.now() < immortalEnd;
    if (bodyMaterial.opacity !== (isGhost ? 0.45 : 1)) {
      bodyMaterial.opacity = isGhost ? 0.45 : 1;
      bodyMaterial.emissiveIntensity = isGhost ? 0.4 : 0.15;
      bodyMaterial.emissive.set(isGhost ? '#3b82f6' : '#1a5c2a');
      bodyMaterial.needsUpdate = true;
    }
  });

  const offsets = eyeOffsets[direction] || eyeOffsets.RIGHT;
  return (
    <group>
      <group ref={bodyGroupRef} />
      <group ref={headRef}>
        <mesh castShadow receiveShadow>
          <sphereGeometry args={[0.32, 16, 16]} />
          <meshPhysicalMaterial
            color="#4ade80"
            roughness={0.25}
            metalness={0.15}
            clearcoat={0.5}
            clearcoatRoughness={0.2}
            emissive="#4ade80"
            emissiveIntensity={0.3}
            envMapIntensity={0.7}
          />
        </mesh>
        <group position={offsets.l}>
          <mesh><sphereGeometry args={[0.075, 8, 8]} /><meshPhysicalMaterial color="white" roughness={0.05} metalness={0.0} clearcoat={1.0} clearcoatRoughness={0.05} /></mesh>
          <mesh position={[0, 0, 0.04]}><sphereGeometry args={[0.04, 8, 8]} /><meshPhysicalMaterial color="#1a1a1a" roughness={0.1} metalness={0.3} /></mesh>
        </group>
        <group position={offsets.r}>
          <mesh><sphereGeometry args={[0.075, 8, 8]} /><meshPhysicalMaterial color="white" roughness={0.05} metalness={0.0} clearcoat={1.0} clearcoatRoughness={0.05} /></mesh>
          <mesh position={[0, 0, 0.04]}><sphereGeometry args={[0.04, 8, 8]} /><meshPhysicalMaterial color="#1a1a1a" roughness={0.1} metalness={0.3} /></mesh>
        </group>
        {tongueOut && <mesh position={[direction === 'LEFT' ? -0.42 : direction === 'RIGHT' ? 0.42 : 0, -0.05, direction === 'UP' ? -0.42 : direction === 'DOWN' ? 0.42 : 0]}><boxGeometry args={[0.025, 0.01, 0.22]} /><meshPhysicalMaterial color="#ef4444" roughness={0.4} metalness={0.0} /></mesh>}
        
        {immortalEnd > 0 && (
          <mesh position={[0, 0, 0]}>
            <sphereGeometry args={[0.5, 16, 16]} />
            <meshPhysicalMaterial
              color="#93c5fd"
              emissive="#3b82f6"
              emissiveIntensity={0.5}
              transparent
              opacity={0.2}
              roughness={0.1}
              metalness={0.3}
            />
          </mesh>
        )}
        
        {slowEnd > 0 && (
          <mesh position={[0, 0, 0]}>
            <sphereGeometry args={[0.48, 16, 16]} />
            <meshPhysicalMaterial
              color="#9ca3af"
              emissive="#6b7280"
              emissiveIntensity={0.25}
              transparent
              opacity={0.12}
              roughness={0.2}
              metalness={0.3}
            />
          </mesh>
        )}
      </group>
    </group>
  );
}

function CpuSnake() {
  const cpuSnake = useGameStore(s => s.cpuSnake);
  const prevCpuSnake = useGameStore(s => s.prevCpuSnake);
  const cpuAlive = useGameStore(s => s.cpuAlive);
  const gridSize = useGameStore(s => s.gridSize);
  const baseSpeed = useGameStore(s => s.baseSpeed);
  const lastCpuMoveTime = useGameStore(s => s.lastCpuMoveTime);
  const cpuImmortalEnd = useGameStore(s => s.cpuImmortalEnd);
  const cpuSpeedBoostEnd = useGameStore(s => s.cpuSpeedBoostEnd);
  const cpuSlowEnd = useGameStore(s => s.cpuSlowEnd);
  const cpuHeadGroupRef = useRef<THREE.Group>(null);
  const bodyGroupRef = useRef<THREE.Group>(null);
  const smoothPositions = useRef<THREE.Vector3[]>(
    cpuSnake.map(seg => { const [wx, , wz] = gridToWorld(seg.x, seg.z, gridSize); return new THREE.Vector3(wx, 0.35, wz); })
  );
  
  const lastBuildKey = useRef<string>('');
  const bodyMaterial = useMemo(() => new THREE.MeshPhysicalMaterial({
    color: '#eab308',
    roughness: 0.25,
    metalness: 0.3,
    clearcoat: 0.6,
    clearcoatRoughness: 0.2,
    emissive: '#92400e',
    emissiveIntensity: 0.15,
    vertexColors: true,
    envMapIntensity: 0.8,
    transparent: true,
    opacity: 1,
  }), []);

  useFrame((_, delta) => {
    if (!cpuAlive || cpuSnake.length === 0) {
      if (bodyGroupRef.current) { while (bodyGroupRef.current.children.length > 0) { const c = bodyGroupRef.current.children[0]; if ((c as THREE.Mesh).geometry) (c as THREE.Mesh).geometry.dispose(); bodyGroupRef.current.remove(c); } }
      lastBuildKey.current = '';
      return;
    }
    const dt = Math.min(delta, 0.1);

    
    const now = Date.now();
    
    const cpuHasBoost = cpuSpeedBoostEnd > 0 && now < cpuSpeedBoostEnd;
    const cpuIsSlowed = cpuSlowEnd > 0 && now < cpuSlowEnd;
    let cpuInterval = baseSpeed;
    if (cpuHasBoost) cpuInterval /= 2;
    if (cpuIsSlowed) cpuInterval *= 2;
    const elapsed = now - lastCpuMoveTime;
    const rawT = cpuInterval > 0 ? Math.min(elapsed / cpuInterval, 1.0) : 1.0;
    const t = rawT * rawT * (3 - 2 * rawT);

    const len = cpuSnake.length;
    const prevLen = prevCpuSnake.length;

    while (smoothPositions.current.length < len) {
      const last = smoothPositions.current[smoothPositions.current.length - 1] || new THREE.Vector3();
      smoothPositions.current.push(last.clone());
    }
    const lengthDecreased = len < smoothPositions.current.length;
    if (lengthDecreased) smoothPositions.current.length = len;

    for (let i = 0; i < len; i++) {
      const [curX, , curZ] = gridToWorld(cpuSnake[i].x, cpuSnake[i].z, gridSize);
      const curTarget = new THREE.Vector3(curX, 0.35, curZ);

      if (i < prevLen && !lengthDecreased) {
        const [prevX, , prevZ] = gridToWorld(prevCpuSnake[i].x, prevCpuSnake[i].z, gridSize);
        const prevTarget = new THREE.Vector3(prevX, 0.35, prevZ);

        if (Math.abs(curX - prevX) > gridSize * 0.4 || Math.abs(curZ - prevZ) > gridSize * 0.4) {
          smoothPositions.current[i].copy(curTarget);
        } else {
          smoothPositions.current[i].lerpVectors(prevTarget, curTarget, t);
        }
      } else {
        smoothPositions.current[i].copy(curTarget);
      }
    }

    if (bodyGroupRef.current && smoothPositions.current.length >= 2) {
      
      const posKey = smoothPositions.current.map(p => `${p.x.toFixed(2)},${p.z.toFixed(2)}`).join('|');
      if (posKey !== lastBuildKey.current) {
        lastBuildKey.current = posKey;
        const segments = buildSnakeSegments(smoothPositions.current, gridSize, '#facc15', '#854d0e', 0.24);
        while (bodyGroupRef.current.children.length > segments.length) { const c = bodyGroupRef.current.children[bodyGroupRef.current.children.length - 1]; if ((c as THREE.Mesh).geometry) (c as THREE.Mesh).geometry.dispose(); bodyGroupRef.current.remove(c); }
        for (let i = 0; i < segments.length; i++) {
          if (i < bodyGroupRef.current.children.length) { const m = bodyGroupRef.current.children[i] as THREE.Mesh; m.geometry.dispose(); m.geometry = segments[i].geometry; }
          else { const m = new THREE.Mesh(segments[i].geometry, bodyMaterial); m.castShadow = true; m.receiveShadow = true; bodyGroupRef.current.add(m); }
        }
      }
    }
    if (cpuHeadGroupRef.current && smoothPositions.current.length > 0) { const hp = smoothPositions.current[0]; cpuHeadGroupRef.current.position.set(hp.x, 0.42, hp.z); }

    
    const isCpuGhost = cpuImmortalEnd > 0 && Date.now() < cpuImmortalEnd;
    if (bodyMaterial.opacity !== (isCpuGhost ? 0.45 : 1)) {
      bodyMaterial.opacity = isCpuGhost ? 0.45 : 1;
      bodyMaterial.emissiveIntensity = isCpuGhost ? 0.4 : 0.15;
      bodyMaterial.emissive.set(isCpuGhost ? '#3b82f6' : '#92400e');
      bodyMaterial.needsUpdate = true;
    }
  });
  if (!cpuAlive) return null;
  return (
    <group>
      <group ref={bodyGroupRef} />
      <group ref={cpuHeadGroupRef}>
        <mesh castShadow receiveShadow>
          <sphereGeometry args={[0.30, 16, 16]} />
          <meshPhysicalMaterial
            color="#facc15"
            roughness={0.2}
            metalness={0.35}
            clearcoat={0.6}
            clearcoatRoughness={0.15}
            emissive={cpuSpeedBoostEnd > 0 ? '#ffffff' : cpuSlowEnd > 0 ? '#6b7280' : cpuImmortalEnd > 0 ? '#3b82f6' : '#eab308'}
            emissiveIntensity={cpuSpeedBoostEnd > 0 ? 0.5 : cpuSlowEnd > 0 ? 0.4 : cpuImmortalEnd > 0 ? 0.6 : 0.3}
            envMapIntensity={0.8}
          />
        </mesh>
        
        {cpuImmortalEnd > 0 && (
          <mesh position={[0, 0, 0]}>
            <sphereGeometry args={[0.5, 16, 16]} />
            <meshPhysicalMaterial
              color="#93c5fd"
              emissive="#3b82f6"
              emissiveIntensity={0.5}
              transparent
              opacity={0.2}
              roughness={0.1}
              metalness={0.3}
            />
          </mesh>
        )}
        
        {cpuSlowEnd > 0 && (
          <mesh position={[0, 0, 0]}>
            <sphereGeometry args={[0.48, 16, 16]} />
            <meshPhysicalMaterial
              color="#9ca3af"
              emissive="#6b7280"
              emissiveIntensity={0.25}
              transparent
              opacity={0.12}
              roughness={0.2}
              metalness={0.3}
            />
          </mesh>
        )}
      </group>
    </group>
  );
}

function Bug() {
  const bug = useGameStore(s => s.bug);
  const gridSize = useGameStore(s => s.gridSize);
  const groupRef = useRef<THREE.Group>(null);
  const smoothPos = useRef<THREE.Vector3 | null>(null);
  const targetQuat = useRef<THREE.Quaternion>(new THREE.Quaternion());
  useFrame((_, delta) => {
    if (!bug || !groupRef.current) return;
    const dt = Math.min(delta, 0.1);
    const [wx, , wz] = gridToWorld(bug.x, bug.z, gridSize);
    const target = new THREE.Vector3(wx, 0.15, wz);

    
    if (smoothPos.current) {
      const moveDir = target.clone().sub(smoothPos.current);
      const moveDist = moveDir.length();
      if (moveDist > 0.01 && moveDist < gridSize * 0.4) {
        
        const angle = Math.atan2(moveDir.x, moveDir.z);
        const targetEuler = new THREE.Euler(0, angle, 0);
        targetQuat.current.setFromEuler(targetEuler);
      }
    }

    
    if (!smoothPos.current) smoothPos.current = target.clone();
    else { if (smoothPos.current.distanceTo(target) > gridSize * 0.4) smoothPos.current.copy(target); else smoothPos.current.lerp(target, 1 - Math.exp(-dt * 12)); }
    groupRef.current.position.copy(smoothPos.current);

    
    groupRef.current.quaternion.slerp(targetQuat.current, 1 - Math.exp(-dt * 8));
  });
  if (!bug) return null;
  return (
    <group ref={groupRef}>
      <mesh castShadow receiveShadow><sphereGeometry args={[0.18, 10, 8]} /><meshPhysicalMaterial color="#1c1917" roughness={0.4} metalness={0.3} clearcoat={0.5} clearcoatRoughness={0.3} /></mesh>
      <mesh position={[0, 0.02, 0.15]} rotation={[0.3, 0, 0]}><sphereGeometry args={[0.1, 8, 8]} /><meshPhysicalMaterial color="#292524" roughness={0.3} metalness={0.4} clearcoat={0.4} clearcoatRoughness={0.3} /></mesh>
      <mesh position={[-0.05, 0.06, 0.22]}><sphereGeometry args={[0.03, 6, 6]} /><meshPhysicalMaterial color="#ef4444" emissive="#ef4444" emissiveIntensity={0.8} roughness={0.1} /></mesh>
      <mesh position={[0.05, 0.06, 0.22]}><sphereGeometry args={[0.03, 6, 6]} /><meshPhysicalMaterial color="#ef4444" emissive="#ef4444" emissiveIntensity={0.8} roughness={0.1} /></mesh>
      {[-0.12, -0.04, 0.04, 0.12].map((zOff, i) => (
        <React.Fragment key={i}>
          <mesh position={[-0.15, -0.08, zOff]} rotation={[0, 0, 0.5]}><cylinderGeometry args={[0.01, 0.01, 0.12, 4]} /><meshPhysicalMaterial color="#44403c" roughness={0.5} metalness={0.2} /></mesh>
          <mesh position={[0.15, -0.08, zOff]} rotation={[0, 0, -0.5]}><cylinderGeometry args={[0.01, 0.01, 0.12, 4]} /><meshPhysicalMaterial color="#44403c" roughness={0.5} metalness={0.2} /></mesh>
        </React.Fragment>
      ))}
      <mesh position={[-0.1, 0.1, -0.02]} rotation={[0.2, 0.3, 0]}><planeGeometry args={[0.14, 0.08]} /><meshPhysicalMaterial color="#57534e" transparent opacity={0.5} side={THREE.DoubleSide} roughness={0.6} metalness={0.1} /></mesh>
      <mesh position={[0.1, 0.1, -0.02]} rotation={[0.2, -0.3, 0]}><planeGeometry args={[0.14, 0.08]} /><meshPhysicalMaterial color="#57534e" transparent opacity={0.5} side={THREE.DoubleSide} roughness={0.6} metalness={0.1} /></mesh>
    </group>
  );
}

function PowerUpApple() {
  const food = useGameStore(s => s.food);
  const gridSize = useGameStore(s => s.gridSize);
  const eatAnimation = useGameStore(s => s.eatAnimation);
  const foodPowerUp = useGameStore(s => s.foodPowerUp);
  const foodSpawnTime = useGameStore(s => s.foodSpawnTime);
  const meshRef = useRef<THREE.Group>(null);
  const [scalePulse, setScalePulse] = useState(1);
  const smoothPos = useRef<THREE.Vector3 | null>(null);
  const matRef = useRef<THREE.MeshPhysicalMaterial>(null);

  
  const goldenMat = useMemo(() => new THREE.MeshPhysicalMaterial({
    color: '#fbbf24', emissive: '#f59e0b', emissiveIntensity: 0.4,
    roughness: 0.15, metalness: 0.6, clearcoat: 1.0, clearcoatRoughness: 0.05,
    envMapIntensity: 1.2, sheen: 0.5, sheenRoughness: 0.2, sheenColor: '#fde68a',
  }), []);
  const immortalMat = useMemo(() => new THREE.MeshPhysicalMaterial({
    color: '#3b82f6', emissive: '#60a5fa', emissiveIntensity: 0.5,
    roughness: 0.1, metalness: 0.2, clearcoat: 1.0, clearcoatRoughness: 0.05,
    envMapIntensity: 1.2, sheen: 0.6, sheenRoughness: 0.1, sheenColor: '#bfdbfe',
    transparent: true, opacity: 0.85,
  }), []);
  const growthMat = useMemo(() => new THREE.MeshPhysicalMaterial({
    color: '#22c55e', emissive: '#16a34a', emissiveIntensity: 0.3,
    roughness: 0.2, metalness: 0.1, clearcoat: 0.7, clearcoatRoughness: 0.15,
    envMapIntensity: 0.8,
  }), []);
  const speedMat = useMemo(() => new THREE.MeshPhysicalMaterial({
    color: '#dc2626', emissive: '#ffffff', emissiveIntensity: 0.5,
    roughness: 0.15, metalness: 0.2, clearcoat: 0.9, clearcoatRoughness: 0.1,
    envMapIntensity: 1.1, sheen: 0.4, sheenRoughness: 0.2, sheenColor: '#ffffff',
  }), []);
  const slowMat = useMemo(() => new THREE.MeshPhysicalMaterial({
    color: '#9ca3af', emissive: '#6b7280', emissiveIntensity: 0.4,
    roughness: 0.3, metalness: 0.4, clearcoat: 0.8, clearcoatRoughness: 0.15,
    envMapIntensity: 0.9, sheen: 0.6, sheenRoughness: 0.15, sheenColor: '#d1d5db',
  }), []);
  const blackMat = useMemo(() => new THREE.MeshPhysicalMaterial({
    color: '#1a1a2e', emissive: '#4a0080', emissiveIntensity: 0.4,
    roughness: 0.1, metalness: 0.6, clearcoat: 1.0, clearcoatRoughness: 0.05,
    envMapIntensity: 1.0, sheen: 0.8, sheenRoughness: 0.1, sheenColor: '#8b5cf6',
  }), []);
  const normalMat = useMemo(() => new THREE.MeshPhysicalMaterial({
    color: '#dc2626', roughness: 0.2, metalness: 0.05,
    clearcoat: 0.8, clearcoatRoughness: 0.1,
    emissive: '#dc2626', emissiveIntensity: 0.05,
    envMapIntensity: 0.9, sheen: 0.3, sheenRoughness: 0.3, sheenColor: '#ff6666',
  }), []);

  const activeMat = foodPowerUp === 'golden' ? goldenMat
    : foodPowerUp === 'immortal' ? immortalMat
    : foodPowerUp === 'growth' ? growthMat
    : foodPowerUp === 'speed' ? speedMat
    : foodPowerUp === 'slow' ? slowMat
    : foodPowerUp === 'black' ? blackMat
    : normalMat;

  const appleScale = foodPowerUp === 'growth' ? 1.15 : foodPowerUp === 'black' ? 1.1 : foodPowerUp === 'immortal' ? 1.05 : foodPowerUp === 'slow' ? 1.05 : 1;
  const rotationSpeed = foodPowerUp === 'speed' ? 4 : foodPowerUp === 'immortal' ? 1.2 : foodPowerUp === 'black' ? 1.5 : foodPowerUp === 'slow' ? 0.3 : 0.8;

  useFrame((state, delta) => {
    if (!meshRef.current) return;
    const dt = Math.min(delta, 0.1);
    const [wx, , wz] = gridToWorld(food.x, food.z, gridSize);
    const target = new THREE.Vector3(wx, 0.35, wz);
    if (!smoothPos.current) smoothPos.current = target.clone();
    else { if (smoothPos.current.distanceTo(target) > gridSize * 0.4) smoothPos.current.copy(target); else smoothPos.current.lerp(target, 1 - Math.exp(-dt * 15)); }
    const t = state.clock.elapsedTime;
    meshRef.current.position.x = smoothPos.current.x;
    meshRef.current.position.y = smoothPos.current.y + Math.sin(t * 2.5) * 0.06;
    meshRef.current.position.z = smoothPos.current.z;
    meshRef.current.rotation.y = t * rotationSpeed;
    const timeSinceEat = Date.now() - eatAnimation;
    if (eatAnimation > 0 && timeSinceEat < 300) setScalePulse(1 + Math.sin(timeSinceEat / 300 * Math.PI) * 0.2);
    else setScalePulse(1);

    
    if (foodPowerUp !== 'none' && foodSpawnTime > 0) {
      const expiryProgress = (Date.now() - foodSpawnTime) / POWERUP_EXPIRY;
      if (expiryProgress > 0.7 && matRef.current) {
        
        const blink = Math.sin(t * 12) > 0 ? 1 : 0.3;
        matRef.current.emissiveIntensity = 0.05 * blink + (1 - 0.05) * 0.1;
      }
    }

    const hour = getGameHour(t);
    const daylight = getDaylight(hour);
    if (matRef.current) matRef.current.emissiveIntensity = 0.05 + (1 - daylight) * 0.12;
  });

  return (
    <group ref={meshRef} scale={scalePulse * appleScale}>
      <mesh castShadow receiveShadow material={activeMat}>
        <sphereGeometry args={[0.32, 16, 16]} />
      </mesh>
      
      <mesh position={[0, 0.25, 0]}><sphereGeometry args={[0.08, 8, 8]} /><meshPhysicalMaterial color={foodPowerUp === 'golden' ? '#92400e' : foodPowerUp === 'black' ? '#2d1b69' : '#991b1b'} roughness={0.4} metalness={0.05} /></mesh>
      <mesh position={[0, 0.42, 0]}><cylinderGeometry args={[0.015, 0.025, 0.15, 6]} /><meshPhysicalMaterial color="#5c3a1e" roughness={0.7} metalness={0.0} /></mesh>
      <mesh position={[0.08, 0.48, 0]} rotation={[0, 0, -0.4]}><planeGeometry args={[0.15, 0.06]} /><meshPhysicalMaterial color={foodPowerUp === 'black' ? '#4a0080' : '#22c55e'} side={THREE.DoubleSide} roughness={0.5} /></mesh>
      <mesh position={[-0.1, 0.1, 0.25]}><sphereGeometry args={[0.06, 8, 8]} /><meshPhysicalMaterial color="white" transparent opacity={0.4} roughness={0} metalness={1} clearcoat={1.0} /></mesh>

      
      {foodPowerUp === 'golden' && (
        <>
          {[0, 1, 2, 3, 4, 5].map(i => {
            const angle = (i / 6) * Math.PI * 2;
            return (
              <mesh key={`spark-${i}`} position={[Math.cos(angle) * 0.45, 0.1 + Math.sin(angle * 2) * 0.05, Math.sin(angle) * 0.45]}>
                <sphereGeometry args={[0.035, 6, 6]} />
                <meshPhysicalMaterial color="#fde68a" emissive="#f59e0b" emissiveIntensity={1.0} roughness={0.1} metalness={0.8} transparent opacity={0.8} />
              </mesh>
            );
          })}
        </>
      )}

      
      {foodPowerUp === 'immortal' && (
        <>
          <mesh>
            <sphereGeometry args={[0.48, 16, 16]} />
            <meshPhysicalMaterial color="#60a5fa" emissive="#3b82f6" emissiveIntensity={0.35} transparent opacity={0.2} roughness={0.1} metalness={0.3} clearcoat={0.8} />
          </mesh>
          
          {[0, 1, 2, 3].map(i => {
            const angle = (i / 4) * Math.PI * 2;
            return (
              <mesh key={`ghost-${i}`} position={[Math.cos(angle) * 0.45, 0.1 + Math.sin(angle) * 0.08, Math.sin(angle) * 0.45]}>
                <sphereGeometry args={[0.05, 6, 6]} />
                <meshPhysicalMaterial color="#bfdbfe" emissive="#60a5fa" emissiveIntensity={1.0} roughness={0.1} metalness={0.2} transparent opacity={0.7} />
              </mesh>
            );
          })}
        </>
      )}

      
      {foodPowerUp === 'speed' && (
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[0.45, 0.03, 8, 24]} />
          <meshPhysicalMaterial color="#ffffff" emissive="#ffffff" emissiveIntensity={0.8} transparent opacity={0.5} roughness={0.1} metalness={0.3} />
        </mesh>
      )}

      
      {foodPowerUp === 'slow' && (
        <>
          <mesh>
            <sphereGeometry args={[0.48, 16, 16]} />
            <meshPhysicalMaterial color="#6b7280" emissive="#9ca3af" emissiveIntensity={0.35} transparent opacity={0.25} roughness={0.2} metalness={0.3} clearcoat={0.5} />
          </mesh>
          
          {[0, 1, 2, 3].map(i => {
            const angle = (i / 4) * Math.PI * 2;
            return (
              <mesh key={`slow-${i}`} position={[Math.cos(angle) * 0.42, 0.1 + Math.sin(angle) * 0.08, Math.sin(angle) * 0.42]}>
                <sphereGeometry args={[0.05, 6, 6]} />
                <meshPhysicalMaterial color="#d1d5db" emissive="#9ca3af" emissiveIntensity={0.8} roughness={0.2} metalness={0.3} transparent opacity={0.6} />
              </mesh>
            );
          })}
        </>
      )}

      
      {foodPowerUp === 'black' && (
        <>
          <mesh>
            <sphereGeometry args={[0.48, 16, 16]} />
            <meshPhysicalMaterial color="#2d1b69" emissive="#7c3aed" emissiveIntensity={0.3} transparent opacity={0.2} roughness={0.1} metalness={0.4} clearcoat={0.6} />
          </mesh>
          
          {[0, 1, 2, 3].map(i => {
            const angle = (i / 4) * Math.PI * 2;
            return (
              <mesh key={`dark-${i}`} position={[Math.cos(angle) * 0.42, -0.1 + Math.sin(angle) * 0.08, Math.sin(angle) * 0.42]}>
                <sphereGeometry args={[0.04, 6, 6]} />
                <meshPhysicalMaterial color="#7c3aed" emissive="#7c3aed" emissiveIntensity={1.0} roughness={0.1} metalness={0.6} transparent opacity={0.7} />
              </mesh>
            );
          })}
        </>
      )}
    </group>
  );
}

function EatParticles() {
  const particles = useGameStore(s => s.particles);
  return (
    <group>{particles.map(p => (
      <mesh key={p.id} position={[p.x, 0.3 + (1 - p.life) * 2, p.z]} scale={p.life * 0.15}>
        <sphereGeometry args={[1, 6, 6]} />
        <meshPhysicalMaterial
          color={p.life > 0.5 ? '#fbbf24' : '#ef4444'}
          emissive={p.life > 0.5 ? '#fbbf24' : '#ef4444'}
          emissiveIntensity={0.8}
          transparent
          opacity={p.life}
          roughness={0.1}
          metalness={0.3}
          clearcoat={0.5}
        />
      </mesh>
    ))}</group>
  );
}

function Tree({ position }: { position: [number, number, number] }) {
  const scale = 0.6 + Math.random() * 0.4;
  return (
    <group position={position} scale={scale}>
      <mesh position={[0, 0.5, 0]} castShadow receiveShadow><cylinderGeometry args={[0.08, 0.12, 1, 8]} /><meshPhysicalMaterial color="#6b3a1f" roughness={0.85} metalness={0.0} clearcoat={0.05} clearcoatRoughness={0.9} /></mesh>
      <mesh position={[0, 1.2, 0]} castShadow receiveShadow><coneGeometry args={[0.5, 0.8, 8]} /><meshPhysicalMaterial color="#2d6b1e" roughness={0.7} metalness={0.0} clearcoat={0.1} clearcoatRoughness={0.7} /></mesh>
      <mesh position={[0, 1.6, 0]} castShadow receiveShadow><coneGeometry args={[0.38, 0.6, 8]} /><meshPhysicalMaterial color="#358524" roughness={0.7} metalness={0.0} clearcoat={0.1} clearcoatRoughness={0.7} /></mesh>
      <mesh position={[0, 1.95, 0]} castShadow receiveShadow><coneGeometry args={[0.25, 0.45, 8]} /><meshPhysicalMaterial color="#3d952c" roughness={0.7} metalness={0.0} clearcoat={0.1} clearcoatRoughness={0.7} /></mesh>
    </group>
  );
}

function Decorations() {
  const gridSize = useGameStore(s => s.gridSize);
  const half = gridSize / 2;
  const trees = useMemo(() => {
    const t: [number, number, number][] = [];
    for (let i = 0; i < 25; i++) {
      const side = Math.floor(Math.random() * 4);
      let x: number, z: number; const off = 1.5;
      switch (side) {
        case 0: x = -half - off - Math.random() * 3; z = (Math.random() - 0.5) * (gridSize + 6); break;
        case 1: x = half + off + Math.random() * 3; z = (Math.random() - 0.5) * (gridSize + 6); break;
        case 2: z = -half - off - Math.random() * 3; x = (Math.random() - 0.5) * (gridSize + 6); break;
        default: z = half + off + Math.random() * 3; x = (Math.random() - 0.5) * (gridSize + 6); break;
      }
      t.push([x, 0, z]);
    }
    return t;
  }, [gridSize, half]);
  return <group>{trees.map((pos, i) => <Tree key={`tree-${i}`} position={pos} />)}</group>;
}

function CameraController() {
  const { camera } = useThree();
  const snake = useGameStore(s => s.snake);
  const status = useGameStore(s => s.status);
  const shakeIntensity = useGameStore(s => s.shakeIntensity);
  const gridSize = useGameStore(s => s.gridSize);
  const shakeRef = useRef(0);
  const camPosSmooth = useRef(new THREE.Vector3(0, 18, 12));
  const lookAtSmooth = useRef(new THREE.Vector3(0, 0, 0));
  useEffect(() => { shakeRef.current = shakeIntensity; }, [shakeIntensity]);

  useFrame((state, delta) => {
    const dt = Math.min(delta, 0.1);
    if (shakeRef.current > 0) { shakeRef.current = Math.max(0, shakeRef.current - dt * 3); useGameStore.setState({ shakeIntensity: shakeRef.current }); }
    const camHeight = gridSize * 0.75 + 4;
    let targetPos: THREE.Vector3; let targetLook: THREE.Vector3;
    if (status === 'menu') {
      const t = state.clock.elapsedTime * 0.15;
      const menuOrbitR = gridSize * 0.45; 
      const menuHeight = camHeight + 3; 
      targetPos = new THREE.Vector3(Math.sin(t) * menuOrbitR, menuHeight, Math.cos(t) * menuOrbitR);
      targetLook = new THREE.Vector3(0, 0, 0);
    } else if (snake.length > 0) {
      const [hx, , hz] = gridToWorld(snake[0].x, snake[0].z, gridSize);
      targetPos = new THREE.Vector3(hx * 0.3, camHeight, hz * 0.3 + gridSize * 0.25);
      targetLook = new THREE.Vector3(hx * 0.4, 0, hz * 0.4);
    } else { targetPos = new THREE.Vector3(0, camHeight, gridSize * 0.3); targetLook = new THREE.Vector3(0, 0, 0); }
    if (shakeRef.current > 0) { targetPos.x += (Math.random() - 0.5) * shakeRef.current * 0.5; targetPos.y += (Math.random() - 0.5) * shakeRef.current * 0.3; }
    const sf = 1 - Math.exp(-dt * 4);
    camPosSmooth.current.lerp(targetPos, sf); lookAtSmooth.current.lerp(targetLook, sf);
    camera.position.copy(camPosSmooth.current); camera.lookAt(lookAtSmooth.current);
  });
  return null;
}

function DayNightLighting() {
  const gridSize = useGameStore(s => s.gridSize);
  const shadowMode = useGameStore(s => s.shadowMode);
  const fixedShadowAngle = useGameStore(s => s.fixedShadowAngle);
  const lampColor = useGameStore(s => s.lampColor);
  const sunLightRef = useRef<THREE.DirectionalLight>(null);
  const moonLightRef = useRef<THREE.DirectionalLight>(null);
  const ambientRef = useRef<THREE.AmbientLight>(null);
  const hemiRef = useRef<THREE.HemisphereLight>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const fogRef = useRef<THREE.Fog>(null);

  const dayAmbient = useMemo(() => new THREE.Color('#b8d4e3'), []);
  const nightAmbient = useMemo(() => new THREE.Color('#101830'), []); 
  const dayFog = useMemo(() => new THREE.Color('#c8ddf0'), []);
  const nightFog = useMemo(() => new THREE.Color('#080c18'), []); 
  const tempColor = useMemo(() => new THREE.Color(), []);
  const tempColor2 = useMemo(() => new THREE.Color(), []);
  const halfExtent = gridSize * 0.6 + 3;

  
  const { scene } = useThree();
  if (sceneRef.current !== scene) sceneRef.current = scene;

  useFrame((state) => {
    const elapsed = state.clock.elapsedTime;
    const hour = getGameHour(elapsed);
    const daylight = getDaylight(hour);
    const sunPos = getSunPosition(hour, gridSize);
    const moonPos = getMoonPosition(hour, gridSize);
    
    const sunElevation = Math.max(0, Math.sin(((hour - 6) / 12) * Math.PI));
    const moonElevation = Math.max(0, Math.sin((((hour - 18) + 24) % 24 / 12) * Math.PI));
    
    const moonFactor = Math.max(0, Math.pow(Math.max(0, Math.sin((((hour - 18) + 24) % 24 / 12) * Math.PI)), 0.5));

    
    const isNightTime = daylight < 0.3;

    
    if (sunLightRef.current) {
      
      
      let effectiveSunPos = sunPos;
      if (shadowMode === 'fixed') {
        const angleRad = (fixedShadowAngle * Math.PI) / 180;
        const dist = gridSize * 1.5;
        effectiveSunPos = new THREE.Vector3(
          Math.cos(angleRad) * dist,
          dist * 0.9,
          Math.sin(angleRad) * dist
        );
      }

      if (sunElevation > 0.01 || shadowMode === 'fixed') {
        sunLightRef.current.position.copy(shadowMode === 'fixed' ? effectiveSunPos : sunPos);
        
        if (shadowMode === 'fixed' && isNightTime) {
          sunLightRef.current.intensity = 0.3; 
        } else if (shadowMode === 'fixed') {
          sunLightRef.current.intensity = 1.8;
        } else {
          sunLightRef.current.intensity = sunElevation * 1.8;
        }
        sunLightRef.current.castShadow = true;
      } else {
        sunLightRef.current.position.set(0, -100, 0);
        sunLightRef.current.intensity = 0;
        sunLightRef.current.castShadow = false;
      }

      
      if (shadowMode === 'fixed' && isNightTime) {
        
        tempColor.set('#b0c8e0');
      } else if (hour > 5 && hour < 8) {
        tempColor.lerpColors(new THREE.Color('#ff8844'), new THREE.Color('#fff5e1'), smoothstep(5, 8, hour));
      } else if (hour > 16 && hour < 19) {
        tempColor.lerpColors(new THREE.Color('#fff5e1'), new THREE.Color('#ff6622'), smoothstep(16, 19, hour));
      } else if (hour >= 8 && hour <= 16) {
        tempColor.set('#fff5e1');
      } else {
        tempColor.set('#ff6622');
      }
      sunLightRef.current.color.copy(tempColor);
    }

    
    if (moonLightRef.current) {
      if (moonElevation > 0.01) {
        moonLightRef.current.position.copy(moonPos);
        moonLightRef.current.intensity = moonFactor * 0.9; 
        moonLightRef.current.castShadow = true;
        
        const moonColor = new THREE.Color('#c8d8f0');
        moonLightRef.current.color.copy(moonColor);
      } else {
        moonLightRef.current.position.set(0, -100, 0);
        moonLightRef.current.intensity = 0;
        moonLightRef.current.castShadow = false;
      }
    }

    
    if (ambientRef.current) {
      tempColor.lerpColors(nightAmbient, dayAmbient, daylight);
      ambientRef.current.color.copy(tempColor);
      ambientRef.current.intensity = 0.12 + daylight * 0.38; 
    }

    
    if (hemiRef.current) {
      hemiRef.current.intensity = 0.08 + daylight * 0.30; 
      const daySkyColor = new THREE.Color('#87ceeb');
      const nightSkyColor = new THREE.Color('#0e1428'); 
      const skyColor = nightSkyColor.clone().lerp(daySkyColor, daylight);
      hemiRef.current.color.copy(skyColor);
    }

    
    if (fogRef.current) {
      tempColor2.lerpColors(nightFog, dayFog, daylight);
      if (hour > 4.5 && hour < 7) { const t = smoothstep(4.5, 7, hour); tempColor2.lerp(new THREE.Color('#ff9966'), (1 - t) * 0.4); }
      if (hour > 16.5 && hour < 20) { const t = smoothstep(16.5, 20, hour); tempColor2.lerp(new THREE.Color('#cc5533'), (1 - t) * 0.5); }
      fogRef.current.color.copy(tempColor2);
      fogRef.current.near = gridSize * (0.8 + daylight * 2.2); 
      fogRef.current.far = gridSize * (2.0 + daylight * 5.0); 
    }

    
    if (sceneRef.current) {
      
      const daySkyBg = new THREE.Color('#6eaadc');   
      const nightSkyBg = new THREE.Color('#060a14'); 
      const sunsetSkyBg = new THREE.Color('#d4694a'); 
      const dawnSkyBg = new THREE.Color('#c88050');   

      const bgColor = nightSkyBg.clone().lerp(daySkyBg, daylight);

      
      if (hour > 16 && hour < 20.5) {
        const sunsetT = smoothstep(16, 18, hour) * (1 - smoothstep(18, 20.5, hour));
        bgColor.lerp(sunsetSkyBg, sunsetT * 0.5);
      }
      if (hour > 4 && hour < 8) {
        const dawnT = smoothstep(4, 5.5, hour) * (1 - smoothstep(5.5, 8, hour));
        bgColor.lerp(dawnSkyBg, dawnT * 0.4);
      }

      sceneRef.current.background = bgColor;
    }
  });

  return (
    <>
      <fog ref={fogRef} attach="fog" args={['#c8ddf0', 80, 200]} />
      <ambientLight ref={ambientRef} intensity={0.4} color="#b8d4e3" />
      <directionalLight
        ref={sunLightRef}
        position={[8, 15, 5]}
        intensity={1.5}
        color="#fff5e1"
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
        shadow-radius={2}
        shadow-bias={-0.0003}
        shadow-normalBias={0.01}
        shadow-camera-near={0.1}
        shadow-camera-far={80}
        shadow-camera-left={-halfExtent}
        shadow-camera-right={halfExtent}
        shadow-camera-top={halfExtent}
        shadow-camera-bottom={-halfExtent}
      />
      <directionalLight
        ref={moonLightRef}
        position={[-8, 15, -5]}
        intensity={0}
        color="#aabbdd"
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
        shadow-radius={2}
        shadow-bias={-0.0005}
        shadow-normalBias={0.01}
        shadow-camera-near={0.1}
        shadow-camera-far={80}
        shadow-camera-left={-halfExtent}
        shadow-camera-right={halfExtent}
        shadow-camera-top={halfExtent}
        shadow-camera-bottom={-halfExtent}
      />
      <hemisphereLight ref={hemiRef} args={['#87ceeb', '#3a7d2c', 0.4]} />
    </>
  );
}

function StarField() {
  const matRef = useRef<THREE.PointsMaterial>(null);
  const geo = useMemo(() => {
    const g = new THREE.BufferGeometry();
    const pos = new Float32Array(300 * 3);
    for (let i = 0; i < 300; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.random() * Math.PI * 0.35;
      const r = 40 + Math.random() * 15;
      pos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = r * Math.cos(phi) + 15;
      pos[i * 3 + 2] = r * Math.sin(phi) * Math.sin(theta);
    }
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    return g;
  }, []);

  useFrame((state) => {
    const hour = getGameHour(state.clock.elapsedTime);
    const daylight = getDaylight(hour);
    if (matRef.current) {
      matRef.current.opacity = Math.max(0, (1 - daylight * 1.8)) * 0.9;
      matRef.current.size = 0.2 + (1 - daylight) * 0.3;
    }
  });

  return (
    <points geometry={geo}>
      <pointsMaterial ref={matRef} color="#ffffff" size={0.3} transparent opacity={0} sizeAttenuation fog={false} />
    </points>
  );
}

function StreetLamps() {
  const gridSize = useGameStore(s => s.gridSize);
  const openSides = useGameStore(s => s.openSides);
  const hasLamps = useGameStore(s => s.hasLamps);
  const lampColor = useGameStore(s => s.lampColor);
  const lampsRef = useRef<THREE.Group>(null);
  const lightRefs = useRef<(THREE.PointLight | null)[]>([]);

  const lampData = useMemo(() => {
    if (!hasLamps) return [];
    const half = gridSize / 2;
    const lamps: { pos: [number, number, number]; }[] = [];
    const spacing = 4;
    if (!openSides.top) { for (let x = -half + 2; x <= half - 2; x += spacing) lamps.push({ pos: [x, 0, -half - 1.5] }); }
    if (!openSides.bottom) { for (let x = -half + 2; x <= half - 2; x += spacing) lamps.push({ pos: [x, 0, half + 1.5] }); }
    if (!openSides.left) { for (let z = -half + 2; z <= half - 2; z += spacing) lamps.push({ pos: [-half - 1.5, 0, z] }); }
    if (!openSides.right) { for (let z = -half + 2; z <= half - 2; z += spacing) lamps.push({ pos: [half + 1.5, 0, z] }); }
    return lamps;
  }, [gridSize, openSides, hasLamps]);

  useFrame((state) => {
    const hour = getGameHour(state.clock.elapsedTime);
    const daylight = getDaylight(hour);
    const nightIntensity = Math.max(0, 1 - daylight * 1.5);
    const isWhite = lampColor === 'white';
    const lightColor = isWhite ? '#c8d8f0' : '#ffcc66'; 
    const emissiveColor = isWhite ? '#c8d8f0' : '#ffcc44';
    lightRefs.current.forEach(light => {
      if (light) {
        light.intensity = nightIntensity * 1.2;
        light.color.set(lightColor);
      }
    });
    if (lampsRef.current) {
      lampsRef.current.children.forEach((child) => {
        const bulb = child.children[2];
        if (bulb && (bulb as THREE.Mesh).material) {
          const mat = (bulb as THREE.Mesh).material as THREE.MeshPhysicalMaterial;
          mat.emissiveIntensity = 0.3 + nightIntensity * 3.0;
          mat.emissive.set(emissiveColor);
          mat.color.set(emissiveColor);
        }
      });
    }
  });

  if (!hasLamps || lampData.length === 0) return null;

  return (
    <group ref={lampsRef}>
      {lampData.map((lamp, i) => (
        <group key={`lamp-${i}`} position={lamp.pos}>
          <mesh position={[0, 0.75, 0]} castShadow><cylinderGeometry args={[0.04, 0.06, 1.5, 6]} /><meshPhysicalMaterial color="#3a3a3a" roughness={0.4} metalness={0.8} clearcoat={0.3} clearcoatRoughness={0.4} /></mesh>
          <mesh position={[0, 1.55, 0]}><cylinderGeometry args={[0.12, 0.08, 0.12, 6]} /><meshPhysicalMaterial color="#4a4a4a" roughness={0.35} metalness={0.7} clearcoat={0.3} /></mesh>
          <mesh position={[0, 1.65, 0]}><sphereGeometry args={[0.07, 8, 8]} /><meshPhysicalMaterial color="#ffcc44" emissive="#ffcc44" emissiveIntensity={0.3} roughness={0.1} metalness={0.0} clearcoat={1.0} clearcoatRoughness={0.05} transmission={0.5} /></mesh>
          <pointLight ref={el => { lightRefs.current[i] = el; }} position={[0, 1.6, 0]} intensity={0} distance={8} decay={2} color="#ffcc66" castShadow />
        </group>
      ))}
    </group>
  );
}

function Fireflies() {
  const hasFireflies = useGameStore(s => s.hasFireflies);
  const groupRef = useRef<THREE.Group>(null);
  const gridSize = useGameStore(s => s.gridSize);
  const lightRefs = useRef<(THREE.PointLight | null)[]>([]);
  const spriteRefs = useRef<(THREE.Sprite | null)[]>([]);

  
  const glowTexture = useMemo(() => {
    const size = 64;
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d')!;
    const center = size / 2;
    const gradient = ctx.createRadialGradient(center, center, 0, center, center, center);
    gradient.addColorStop(0, 'rgba(255, 240, 120, 1.0)');
    gradient.addColorStop(0.1, 'rgba(255, 230, 80, 0.9)');
    gradient.addColorStop(0.3, 'rgba(255, 210, 50, 0.4)');
    gradient.addColorStop(0.6, 'rgba(200, 180, 30, 0.1)');
    gradient.addColorStop(1.0, 'rgba(150, 130, 10, 0.0)');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, size, size);
    const tex = new THREE.CanvasTexture(canvas);
    tex.needsUpdate = true;
    return tex;
  }, []);

  const fireflyData = useMemo(() => {
    if (!hasFireflies) return [];
    return Array.from({ length: 22 }, () => ({
      baseX: (Math.random() - 0.5) * gridSize * 0.9,
      baseZ: (Math.random() - 0.5) * gridSize * 0.9,
      baseY: 0.4 + Math.random() * 1.0,
      speed: 0.25 + Math.random() * 0.5,
      phase: Math.random() * Math.PI * 2,
      drift: 0.2 + Math.random() * 0.4,
      blinkSpeed: 1.5 + Math.random() * 2.5,
      blinkPhase: Math.random() * Math.PI * 2,
    }));
  }, [hasFireflies, gridSize]);

  useFrame((state) => {
    if (!groupRef.current) return;
    const elapsed = state.clock.elapsedTime;
    const hour = getGameHour(elapsed);
    const daylight = getDaylight(hour);
    const nightFactor = Math.max(0, 1 - daylight * 1.5);
    groupRef.current.visible = nightFactor > 0.1;
    groupRef.current.children.forEach((child, i) => {
      const data = fireflyData[i];
      if (!data) return;
      const t = elapsed * data.speed + data.phase;
      
      const blinkCycle = Math.sin(t * data.blinkSpeed + data.blinkPhase);
      const blinkOn = Math.max(0, Math.sin(blinkCycle * Math.PI * 0.8));
      const blinkEnvelope = Math.max(0, Math.sin(t * 0.5 + data.phase) * 0.5 + 0.5);
      const brightness = Math.max(0, nightFactor * blinkOn * blinkEnvelope);

      
      child.position.x = data.baseX + Math.sin(t * 0.7) * data.drift;
      child.position.y = data.baseY + Math.sin(t * 0.9) * 0.2;
      child.position.z = data.baseZ + Math.cos(t * 0.5) * data.drift;

      
      const sprite = spriteRefs.current[i];
      if (sprite) {
        const pulseScale = 0.15 + brightness * 0.35 + Math.sin(t * 3.0) * brightness * 0.05;
        sprite.scale.set(pulseScale, pulseScale, 1);
        (sprite.material as THREE.SpriteMaterial).opacity = brightness * 0.9;
      }

      
      if (i % 4 === 0) {
        const lightIdx = Math.floor(i / 4);
        const light = lightRefs.current[lightIdx];
        if (light) {
          light.position.copy(child.position);
          light.intensity = brightness * 0.3;
        }
      }
    });
  });

  if (!hasFireflies) return null;

  return (
    <group ref={groupRef}>
      {fireflyData.map((_, i) => (
        <group key={`ff-${i}`} position={[0, 0.5, 0]}>
          
          <sprite
            ref={el => { spriteRefs.current[i] = el; }}
            scale={[0.15, 0.15, 1]}
          >
            <spriteMaterial
              map={glowTexture}
              color="#ffe866"
              transparent
              opacity={0}
              blending={THREE.AdditiveBlending}
              depthWrite={false}
            />
          </sprite>
          
          {i % 4 === 0 && (
            <pointLight
              ref={el => { lightRefs.current[Math.floor(i / 4)] = el; }}
              intensity={0}
              distance={6}
              decay={2}
              color="#eedd44"
            />
          )}
        </group>
      ))}
    </group>
  );
}

function ExtendedGround() {
  const gridSize = useGameStore(s => s.gridSize);
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]} receiveShadow>
      <planeGeometry args={[gridSize + 40, gridSize + 40]} />
      <meshPhysicalMaterial color="#2d6b1e" roughness={0.95} metalness={0.0} clearcoat={0.02} />
    </mesh>
  );
}

interface CloudPuff {
  x: number; z: number; y: number;        
  scaleX: number; scaleY: number; scaleZ: number;  
  windSpeed: number;                       
  phase: number;                           
  opacity: number;                         
}

interface CloudCluster {
  puffs: CloudPuff[];
  baseX: number;
  baseZ: number;
}

function createCloudTexture(): THREE.CanvasTexture {
  const size = 128;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d')!;
  const cx = size / 2;
  const cy = size / 2;
  
  const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, cx);
  gradient.addColorStop(0, 'rgba(255, 255, 255, 1.0)');
  gradient.addColorStop(0.15, 'rgba(255, 255, 255, 0.95)');
  gradient.addColorStop(0.35, 'rgba(250, 250, 255, 0.7)');
  gradient.addColorStop(0.55, 'rgba(245, 248, 255, 0.35)');
  gradient.addColorStop(0.75, 'rgba(240, 245, 255, 0.1)');
  gradient.addColorStop(1.0, 'rgba(235, 240, 255, 0.0)');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(canvas);
  tex.needsUpdate = true;
  return tex;
}

function createCloudShadowTexture(): THREE.CanvasTexture {
  const size = 64;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d')!;
  const cx = size / 2;
  const cy = size / 2;
  const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, cx);
  gradient.addColorStop(0, 'rgba(0, 0, 0, 0.5)');
  gradient.addColorStop(0.3, 'rgba(0, 0, 0, 0.3)');
  gradient.addColorStop(0.6, 'rgba(0, 0, 0, 0.1)');
  gradient.addColorStop(1.0, 'rgba(0, 0, 0, 0.0)');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(canvas);
  tex.needsUpdate = true;
  return tex;
}

function VolumetricClouds() {
  const gridSize = useGameStore(s => s.gridSize);
  const groupRef = useRef<THREE.Group>(null);

  
  const cloudTexture = useMemo(() => createCloudTexture(), []);
  const shadowTexture = useMemo(() => createCloudShadowTexture(), []);

  
  const cloudClusters = useMemo((): CloudCluster[] => {
    const clusters: CloudCluster[] = [];
    const numClusters = 12 + Math.floor(Math.random() * 6); 
    const half = gridSize * 0.8;
    for (let c = 0; c < numClusters; c++) {
      const baseX = (Math.random() - 0.5) * half * 2;
      const baseZ = (Math.random() - 0.5) * half * 2;
      const numPuffs = 3 + Math.floor(Math.random() * 5); 
      const puffs: CloudPuff[] = [];
      for (let p = 0; p < numPuffs; p++) {
        puffs.push({
          x: (Math.random() - 0.5) * 4 + baseX,   
          z: (Math.random() - 0.5) * 4 + baseZ,
          y: 3.5 + Math.random() * 4,               
          scaleX: 2.5 + Math.random() * 3,          
          scaleY: 0.8 + Math.random() * 1.2,         
          scaleZ: 2.5 + Math.random() * 3,
          windSpeed: 0.6 + Math.random() * 1.2,      
          phase: Math.random() * Math.PI * 2,
          opacity: 0.4 + Math.random() * 0.4,         
        });
      }
      clusters.push({ puffs, baseX, baseZ });
    }
    return clusters;
  }, [gridSize]);

  
  const allPuffs = useMemo(() => cloudClusters.flatMap(c => c.puffs), [cloudClusters]);

  
  const cloudMaterials = useMemo(() =>
    allPuffs.map(() => new THREE.SpriteMaterial({
      map: cloudTexture,
      transparent: true,
      depthWrite: false,
      blending: THREE.NormalBlending,
      fog: true,
    })),
  [allPuffs, cloudTexture]);

  const shadowMaterials = useMemo(() =>
    allPuffs.map(() => new THREE.SpriteMaterial({
      map: shadowTexture,
      transparent: true,
      depthWrite: false,
      blending: THREE.NormalBlending,
      opacity: 0.3,
      fog: false,
    })),
  [allPuffs, shadowTexture]);

  
  const cloudSpriteRefs = useRef<(THREE.Sprite | null)[]>([]);
  const shadowSpriteRefs = useRef<(THREE.Sprite | null)[]>([]);

  
  const dayColorRef = useRef(new THREE.Color(1.0, 1.0, 1.0));
  const nightColorRef = useRef(new THREE.Color(0.15, 0.18, 0.25));
  const sunsetColorRef = useRef(new THREE.Color(1.0, 0.6, 0.35));
  const tempColorRef = useRef(new THREE.Color());

  useFrame((state) => {
    const elapsed = state.clock.elapsedTime;
    const hour = getGameHour(elapsed);
    const daylight = getDaylight(hour);
    const windBase = elapsed * 0.8; 

    
    const sunset = smoothstep(0.3, 0.6, daylight) * (1 - smoothstep(0.6, 0.9, daylight));

    
    const color = tempColorRef.current.copy(nightColorRef.current).lerp(dayColorRef.current, daylight);
    color.lerp(sunsetColorRef.current, sunset * 0.4);

    const baseCloudOpacity = 0.15 + daylight * 0.6;
    const baseShadowOpacity = daylight * 0.25;

    
    allPuffs.forEach((puff, i) => {
      const cloudSprite = cloudSpriteRefs.current[i];
      const shadowSprite = shadowSpriteRefs.current[i];
      const cloudMat = cloudMaterials[i];
      const shadowMat = shadowMaterials[i];
      if (!cloudSprite || !cloudMat) return;

      
      const driftX = Math.sin(elapsed * 0.1 + puff.phase) * 0.3 + windBase * puff.windSpeed;
      const driftZ = Math.cos(elapsed * 0.08 + puff.phase * 1.3) * 0.2;

      
      const wrapRange = gridSize * 1.2;
      let posX = puff.x + driftX;
      let posZ = puff.z + driftZ;
      
      while (posX > wrapRange) posX -= wrapRange * 2;
      while (posX < -wrapRange) posX += wrapRange * 2;
      
      while (posZ > wrapRange) posZ -= wrapRange * 2;
      while (posZ < -wrapRange) posZ += wrapRange * 2;

      
      const posY = puff.y + Math.sin(elapsed * 0.3 + puff.phase) * 0.15;

      cloudSprite.position.set(posX, posY, posZ);
      
      const pulseScale = 1.0 + Math.sin(elapsed * 0.5 + puff.phase) * 0.03;
      cloudSprite.scale.set(puff.scaleX * pulseScale, puff.scaleY * pulseScale, 1);

      
      cloudMat.color.copy(color);
      cloudMat.opacity = puff.opacity * baseCloudOpacity;

      
      if (shadowSprite && shadowMat) {
        shadowSprite.position.set(posX, 0.06, posZ);
        
        shadowSprite.scale.set(puff.scaleX * 1.3, puff.scaleZ * 1.3, 1);
        shadowMat.opacity = puff.opacity * baseShadowOpacity; 
      }
    });
  });

  return (
    <group ref={groupRef}>
      
      {allPuffs.map((puff, i) => (
        <React.Fragment key={`cloud-${i}`}>
          <sprite
            ref={el => { cloudSpriteRefs.current[i] = el; }}
            position={[puff.x, puff.y, puff.z]}
            scale={[puff.scaleX, puff.scaleY, 1]}
            material={cloudMaterials[i]}
            renderOrder={10}
          />
          
          <sprite
            ref={el => { shadowSpriteRefs.current[i] = el; }}
            position={[puff.x, 0.06, puff.z]}
            scale={[puff.scaleX * 1.3, puff.scaleZ * 1.3, 1]}
            material={shadowMaterials[i]}
            renderOrder={5}
          />
        </React.Fragment>
      ))}
    </group>
  );
}

export default function SnakeScene() {
  const gridSize = useGameStore(s => s.gridSize);
  const cloudsEnabled = useGameStore(s => s.cloudsEnabled);

  return (
    <Canvas
      shadows
      dpr={[1, 2]}
      camera={{ position: [0, gridSize * 0.75 + 4, gridSize * 0.3], fov: 50, near: 0.1, far: 150 }}
      style={{ width: '100%', height: '100%' }}
      gl={{
        antialias: true,
        toneMapping: THREE.ACESFilmicToneMapping,
        toneMappingExposure: 1.0,
        powerPreference: 'high-performance',
      }}
      onCreated={({ gl }) => {
        gl.shadowMap.type = THREE.PCFSoftShadowMap;
        gl.shadowMap.needsUpdate = true;
      }}
    >
      <ShadowSetup />
      <DynamicExposure />
      <DayNightLighting />
      <ExtendedGround />
      <Ground />
      <BorderWalls />
      <InteriorWalls />
      <Decorations />
      <StreetLamps />
      <Fireflies />
      <Snake />
      <CpuSnake />
      <Bug />
      <PowerUpApple />
      <EatParticles />
      <CameraController />
      <StarField />
      {cloudsEnabled && <VolumetricClouds />}
      <PathTracer />
    </Canvas>
  );
}
