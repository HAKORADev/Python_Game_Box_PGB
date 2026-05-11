export const CLASSIC_GRID_SIZE = 20;
export const CELL_SIZE = 1;
export const MIN_ARCADE_GRID = 14;
export const MAX_ARCADE_GRID = 24;
export const INITIAL_SPEED = 200; 
export const MIN_SPEED = 80;
export const SPEED_DECREASE = 3; 
export const BUG_PENALTY_LENGTH = 10;
export const BUG_PENALTY_SCORE = 10;
export const CYCLE_SECONDS = 720; 

export const DIRECTION = {
  UP: { x: 0, z: -1 },
  DOWN: { x: 0, z: 1 },
  LEFT: { x: -1, z: 0 },
  RIGHT: { x: 1, z: 0 },
} as const;

export type DirectionKey = keyof typeof DIRECTION;
export type Position = { x: number; z: number };
export type MapMode = 'classic' | 'arcade';

export interface OpenSides {
  top: boolean;    
  bottom: boolean; 
  left: boolean;   
  right: boolean;  
}

export interface MapConfig {
  gridSize: number;
  walls: Position[];
  openSides: OpenSides;
  hasCpuSnake: boolean;
  hasBug: boolean;
  hasLamps: boolean;
  hasFireflies: boolean;
}

export const NO_OPEN_SIDES: OpenSides = { top: false, bottom: false, left: false, right: false };
export const ALL_OPEN_SIDES: OpenSides = { top: true, bottom: true, left: true, right: true };

export const OPPOSITE: Record<DirectionKey, DirectionKey> = {
  UP: 'DOWN',
  DOWN: 'UP',
  LEFT: 'RIGHT',
  RIGHT: 'LEFT',
};

export function gridToWorld(gx: number, gz: number, gridSize: number): [number, number, number] {
  const half = gridSize / 2;
  return [
    (gx - half + 0.5) * CELL_SIZE,
    0,
    (gz - half + 0.5) * CELL_SIZE,
  ];
}

export function posKey(p: Position): string {
  return `${p.x},${p.z}`;
}

export function randomFoodPosition(
  gridSize: number,
  occupied: Set<string>
): Position {
  const available: Position[] = [];
  for (let x = 0; x < gridSize; x++) {
    for (let z = 0; z < gridSize; z++) {
      if (!occupied.has(`${x},${z}`)) {
        available.push({ x, z });
      }
    }
  }
  if (available.length === 0) return { x: 0, z: 0 };
  return available[Math.floor(Math.random() * available.length)];
}

export function wrapPos(val: number, gridSize: number): number {
  if (val < 0) return gridSize - 1;
  if (val >= gridSize) return 0;
  return val;
}

export function applyWrap(
  x: number, z: number, gridSize: number, openSides: OpenSides
): { x: number; z: number; hitWall: boolean } {
  let hitWall = false;
  let nx = x, nz = z;
  if (nx < 0) { if (openSides.left) nx = gridSize - 1; else hitWall = true; }
  else if (nx >= gridSize) { if (openSides.right) nx = 0; else hitWall = true; }
  if (nz < 0) { if (openSides.top) nz = gridSize - 1; else hitWall = true; }
  else if (nz >= gridSize) { if (openSides.bottom) nz = 0; else hitWall = true; }
  return { x: nx, z: nz, hitWall };
}

export function hasAnyOpenSide(openSides: OpenSides): boolean {
  return openSides.top || openSides.bottom || openSides.left || openSides.right;
}

export type TimeMode = 'cycle' | 'day' | 'night' | 'custom';
export type ShadowMode = 'dynamic' | 'fixed';
export type LampColorMode = 'yellow' | 'white';

export type PowerUpType = 'none' | 'golden' | 'immortal' | 'growth' | 'speed' | 'slow' | 'black';

export const POWERUP_CHANCE = 0.20; 
export const POWERUP_DISTRIBUTION: { type: PowerUpType; chance: number }[] = [
  { type: 'golden', chance: 0.28 },
  { type: 'immortal', chance: 0.18 },
  { type: 'growth', chance: 0.15 },
  { type: 'speed', chance: 0.12 },
  { type: 'slow', chance: 0.12 },
  { type: 'black', chance: 0.15 },
];
export const POWERUP_EXPIRY = 10000; 
export const SPEED_BOOST_DURATION = 25000; 
export const SPEED_BOOST_MULTIPLIER = 2;
export const SLOW_DURATION = 25000; 
export const SLOW_MULTIPLIER = 2; 
export const IMMORTAL_DURATION = 10000; 
export const BLACK_APPLE_LENGTH_PENALTY = 5; 

export function rollPowerUp(): PowerUpType {
  if (Math.random() >= POWERUP_CHANCE) return 'none';
  let roll = Math.random();
  for (const entry of POWERUP_DISTRIBUTION) {
    roll -= entry.chance;
    if (roll <= 0) return entry.type;
  }
  return POWERUP_DISTRIBUTION[POWERUP_DISTRIBUTION.length - 1].type;
}

export function getEffectiveHour(timeMode: TimeMode, elapsed: number, customHour?: number): number {
  if (timeMode === 'day') return 12;
  if (timeMode === 'night') return 0;
  if (timeMode === 'custom') return customHour ?? 12;
  return ((elapsed % CYCLE_SECONDS) / CYCLE_SECONDS) * 24;
}

export function smoothstep(e0: number, e1: number, x: number): number {
  const t = Math.max(0, Math.min(1, (x - e0) / (e1 - e0)));
  return t * t * (3 - 2 * t);
}

export function getGameHour(elapsed: number): number {
  
  const { useGameStore } = require('./store');
  const timeMode = useGameStore.getState().timeMode;
  const customHour = useGameStore.getState().customTimeHour + useGameStore.getState().customTimeMinute / 60;
  return getEffectiveHour(timeMode, elapsed, customHour);
}

export function getDaylight(hour: number): number {
  if (hour >= 8 && hour <= 16) return 1;
  if (hour >= 20.5 || hour <= 4) return 0;
  if (hour > 4 && hour < 8) return smoothstep(4, 8, hour);
  return 1 - smoothstep(16, 20.5, hour);
}

export function getSunPosition(hour: number, gridSize: number): { x: number; y: number; z: number } {
  const angle = ((hour - 6) / 12) * Math.PI;
  const elevation = Math.sin(angle);
  const azimuth = Math.cos(angle);
  const dist = gridSize * 1.5;
  return { x: azimuth * dist, y: elevation * dist * 0.9, z: -dist * 0.3 };
}

export function getMoonPosition(hour: number, gridSize: number): { x: number; y: number; z: number } {
  const moonHour = ((hour - 18) + 24) % 24;
  const angle = (moonHour / 12) * Math.PI;
  const elevation = Math.sin(angle);
  const azimuth = Math.cos(angle);
  const dist = gridSize * 1.5;
  return { x: -azimuth * dist, y: elevation * dist * 0.8, z: dist * 0.3 };
}

function generateOpenSides(): OpenSides {
  const r = Math.random();
  if (r < 0.45) {
    
    return { ...NO_OPEN_SIDES };
  } else if (r < 0.55) {
    
    return { ...ALL_OPEN_SIDES };
  } else {
    
    const numOpen = 1 + Math.floor(Math.random() * 3);
    const sides: (keyof OpenSides)[] = ['top', 'bottom', 'left', 'right'];
    
    for (let i = sides.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [sides[i], sides[j]] = [sides[j], sides[i]];
    }
    const result: OpenSides = { ...NO_OPEN_SIDES };
    for (let i = 0; i < numOpen; i++) {
      result[sides[i]] = true;
    }
    return result;
  }
}

function generateMazeWalls(
  gridSize: number,
  safeZone: Set<string>
): Position[] {
  const walls: Position[] = [];
  const wallSet = new Set<string>();

  
  recursiveDivision(1, 1, gridSize - 2, gridSize - 2, walls, wallSet, safeZone);

  
  const removalCount = Math.floor(walls.length * 0.2);
  for (let i = 0; i < removalCount; i++) {
    if (walls.length === 0) break;
    const idx = Math.floor(Math.random() * walls.length);
    const removed = walls.splice(idx, 1)[0];
    wallSet.delete(posKey(removed));
  }

  
  if (!isConnected(wallSet, gridSize)) {
    let attempts = 0;
    while (!isConnected(wallSet, gridSize) && walls.length > 0 && attempts < 100) {
      const idx = Math.floor(Math.random() * walls.length);
      const removed = walls.splice(idx, 1)[0];
      wallSet.delete(posKey(removed));
      attempts++;
    }
  }

  return walls;
}

function recursiveDivision(
  x1: number, z1: number, x2: number, z2: number,
  walls: Position[], wallSet: Set<string>, safeZone: Set<string>
) {
  const width = x2 - x1;
  const height = z2 - z1;

  if (width < 3 || height < 3) return;

  
  const horizontal = height > width
    ? true
    : width > height
      ? false
      : Math.random() < 0.5;

  if (horizontal) {
    if (height < 4) return; 
    
    const wallZ = z1 + 2 + Math.floor(Math.random() * (height - 3));
    
    const gapX1 = x1 + Math.floor(Math.random() * width);
    const gapX2 = Math.random() < 0.35 ? x1 + Math.floor(Math.random() * width) : -1;

    for (let x = x1; x <= x2; x++) {
      
      if (x === gapX1 || x === gapX1 + 1) continue;
      if (gapX2 >= 0 && (x === gapX2 || x === gapX2 + 1)) continue;
      const key = `${x},${wallZ}`;
      if (!safeZone.has(key) && !wallSet.has(key)) {
        wallSet.add(key);
        walls.push({ x, z: wallZ });
      }
    }

    recursiveDivision(x1, z1, x2, wallZ - 1, walls, wallSet, safeZone);
    recursiveDivision(x1, wallZ + 1, x2, z2, walls, wallSet, safeZone);
  } else {
    if (width < 4) return;
    const wallX = x1 + 2 + Math.floor(Math.random() * (width - 3));
    const gapZ1 = z1 + Math.floor(Math.random() * height);
    const gapZ2 = Math.random() < 0.35 ? z1 + Math.floor(Math.random() * height) : -1;

    for (let z = z1; z <= z2; z++) {
      if (z === gapZ1 || z === gapZ1 + 1) continue;
      if (gapZ2 >= 0 && (z === gapZ2 || z === gapZ2 + 1)) continue;
      const key = `${wallX},${z}`;
      if (!safeZone.has(key) && !wallSet.has(key)) {
        wallSet.add(key);
        walls.push({ x: wallX, z });
      }
    }

    recursiveDivision(x1, z1, wallX - 1, z2, walls, wallSet, safeZone);
    recursiveDivision(wallX + 1, z1, x2, z2, walls, wallSet, safeZone);
  }
}

function isConnected(wallSet: Set<string>, gridSize: number): boolean {
  
  let start: Position | null = null;
  for (let x = 0; x < gridSize && !start; x++) {
    for (let z = 0; z < gridSize && !start; z++) {
      if (!wallSet.has(`${x},${z}`)) {
        start = { x, z };
      }
    }
  }
  if (!start) return false;

  const visited = new Set<string>();
  const queue: Position[] = [start];
  visited.add(posKey(start));

  while (queue.length > 0) {
    const curr = queue.shift()!;
    for (const [dx, dz] of [[0, 1], [0, -1], [1, 0], [-1, 0]]) {
      const nx = curr.x + dx;
      const nz = curr.z + dz;
      const key = `${nx},${nz}`;
      if (nx >= 0 && nx < gridSize && nz >= 0 && nz < gridSize &&
          !wallSet.has(key) && !visited.has(key)) {
        visited.add(key);
        queue.push({ x: nx, z: nz });
      }
    }
  }

  let totalOpen = 0;
  for (let x = 0; x < gridSize; x++) {
    for (let z = 0; z < gridSize; z++) {
      if (!wallSet.has(`${x},${z}`)) totalOpen++;
    }
  }

  return visited.size === totalOpen;
}

export function generateArcadeMap(): MapConfig {
  const gridSize = MIN_ARCADE_GRID + Math.floor(Math.random() * (MAX_ARCADE_GRID - MIN_ARCADE_GRID + 1));

  
  let hasWalls = Math.random() < 0.65;
  const openSides = generateOpenSides();
  const hasCpuSnake = Math.random() < 0.40;
  const hasBug = Math.random() < 0.35;

  
  if (!hasWalls && !hasAnyOpenSide(openSides) && !hasCpuSnake && !hasBug) {
    const features = ['walls', 'cpu', 'bug', 'open'] as const;
    const pick = features[Math.floor(Math.random() * features.length)];
    if (pick === 'walls') hasWalls = true;
  }

  const walls: Position[] = [];

  if (hasWalls) {
    
    const safeZone = new Set<string>();
    const cx = Math.floor(gridSize / 2);
    const cz = Math.floor(gridSize / 2);
    for (let dx = -3; dx <= 3; dx++) {
      for (let dz = -3; dz <= 3; dz++) {
        safeZone.add(`${cx + dx},${cz + dz}`);
      }
    }
    
    if (hasCpuSnake) {
      for (let dx = 0; dx < 5; dx++) {
        for (let dz = 0; dz < 5; dz++) {
          safeZone.add(`${1 + dx},${1 + dz}`);
        }
      }
    }

    const mazeWalls = generateMazeWalls(gridSize, safeZone);
    walls.push(...mazeWalls);
  }

  const hasLamps = Math.random() < 0.40;
  const hasFireflies = Math.random() < 0.50;

  return { gridSize, walls, openSides, hasCpuSnake, hasBug, hasLamps, hasFireflies };
}
