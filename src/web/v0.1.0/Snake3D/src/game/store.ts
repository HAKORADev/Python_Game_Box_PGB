import { create } from 'zustand';
import {
  CLASSIC_GRID_SIZE,
  INITIAL_SPEED,
  MIN_SPEED,
  SPEED_DECREASE,
  BUG_PENALTY_LENGTH,
  BUG_PENALTY_SCORE,
  DIRECTION,
  OPPOSITE,
  DirectionKey,
  Position,
  MapMode,
  MapConfig,
  OpenSides,
  NO_OPEN_SIDES,
  posKey,
  randomFoodPosition,
  applyWrap,
  generateArcadeMap,
  TimeMode,
  ShadowMode,
  LampColorMode,
  PowerUpType,
  rollPowerUp,
  POWERUP_EXPIRY,
  SPEED_BOOST_DURATION,
  SPEED_BOOST_MULTIPLIER,
  SLOW_DURATION,
  SLOW_MULTIPLIER,
  IMMORTAL_DURATION,
  BLACK_APPLE_LENGTH_PENALTY,
} from './constants';

export type GameStatus = 'menu' | 'playing' | 'paused' | 'gameover';
export type GameResult = 'won' | 'lost' | 'tied' | null;

interface Particle {
  id: number;
  x: number;
  z: number;
  vx: number;
  vz: number;
  life: number;
}

interface GameState {
  
  mode: MapMode;
  mapConfig: MapConfig | null;
  gridSize: number;
  wallSet: Set<string>;
  openSides: OpenSides;

  
  snake: Position[];
  prevSnake: Position[];
  direction: DirectionKey;
  nextDirection: DirectionKey;

  
  cpuSnake: Position[];
  prevCpuSnake: Position[];
  cpuDirection: DirectionKey;
  cpuScore: number;
  cpuAlive: boolean;

  
  lastTickTime: number;
  lastPlayerMoveTime: number; 
  lastCpuMoveTime: number; 

  
  bug: Position | null;
  bugPrevPos: Position | null;
  bugTickCount: number;
  bugMoveAccum: number; 

  
  hasLamps: boolean;
  hasFireflies: boolean;

  
  food: Position;
  score: number;
  highScore: number;

  
  status: GameStatus;
  speed: number; 
  baseSpeed: number; 
  playerMoveAccum: number; 
  cpuMoveAccum: number; 

  
  timeMode: TimeMode;
  customTimeHour: number; 
  customTimeMinute: number; 

  
  cloudsEnabled: boolean;
  shadowMode: ShadowMode;
  fixedShadowAngle: number; 
  lampColor: LampColorMode;

  
  masterVolume: number; 

  
  foodPowerUp: PowerUpType;
  foodSpawnTime: number; 
  immortalEnd: number; 
  speedBoostEnd: number;
  slowEnd: number; 

  
  cpuImmortalEnd: number; 
  cpuSpeedBoostEnd: number;
  cpuSlowEnd: number; 

  
  particles: Particle[];
  lastParticleId: number;
  eatAnimation: number;
  shakeIntensity: number;
  gameResult: GameResult;
  bugHitTime: number;

  
  setMode: (mode: MapMode) => void;
  setTimeMode: (mode: TimeMode) => void;
  setCustomTime: (hour: number, minute: number) => void;
  setCloudsEnabled: (enabled: boolean) => void;
  setShadowMode: (mode: ShadowMode) => void;
  setFixedShadowAngle: (angle: number) => void;
  setLampColor: (color: LampColorMode) => void;
  setMasterVolume: (volume: number) => void;
  startGame: () => void;
  goToMenu: () => void;
  pauseGame: () => void;
  resumeGame: () => void;
  setDirection: (dir: DirectionKey) => void;
  tick: () => void;
  spawnParticles: (x: number, z: number) => void;
  updateParticles: (dt: number) => void;
}

const INITIAL_SNAKE: Position[] = [
  { x: 10, z: 10 },
  { x: 9, z: 10 },
  { x: 8, z: 10 },
];

const loadHighScore = (): number => {
  if (typeof window === 'undefined') return 0;
  try { return parseInt(localStorage.getItem('snake3d_highscore') || '0', 10); }
  catch { return 0; }
};

const saveHighScore = (score: number) => {
  try { localStorage.setItem('snake3d_highscore', String(score)); }
  catch {  }
};

function getOccupiedSet(
  snake: Position[],
  cpuSnake: Position[],
  walls: Position[],
  bug: Position | null,
  food: Position
): Set<string> {
  const s = new Set<string>();
  snake.forEach(p => s.add(posKey(p)));
  cpuSnake.forEach(p => s.add(posKey(p)));
  walls.forEach(p => s.add(posKey(p)));
  if (bug) s.add(posKey(bug));
  s.add(posKey(food));
  return s;
}

const cpuRecentPositions: Position[] = [];
const CPU_POSITION_HISTORY = 12; 
const CPU_BFS_LIMIT = 200; 

function getCpuPositionKey(p: Position): string {
  return `${p.x},${p.z}`;
}

function buildObstacleSet(
  cpuSnake: Position[],
  playerSnake: Position[],
  wallSet: Set<string>,
  bug: Position | null
): Set<string> {
  const s = new Set<string>();
  
  for (let i = 0; i < cpuSnake.length - 1; i++) s.add(getCpuPositionKey(cpuSnake[i]));
  for (const seg of playerSnake) s.add(getCpuPositionKey(seg));
  for (const w of wallSet) s.add(w); 
  if (bug) s.add(getCpuPositionKey(bug));
  return s;
}

function isNavigable(
  x: number, z: number,
  gridSize: number, openSides: OpenSides,
  obstacleSet: Set<string>, visited: Set<string>
): { ok: boolean; wx: number; wz: number } {
  const wrap = applyWrap(x, z, gridSize, openSides);
  if (wrap.hitWall) return { ok: false, wx: x, wz: z };
  const key = `${wrap.x},${wrap.z}`;
  if (obstacleSet.has(key) || visited.has(key)) return { ok: false, wx: wrap.x, wz: wrap.z };
  return { ok: true, wx: wrap.x, wz: wrap.z };
}

function bfsPathToFood(
  cpuSnake: Position[],
  food: Position,
  wallSet: Set<string>,
  playerSnake: Position[],
  gridSize: number,
  openSides: OpenSides,
  bug: Position | null,
  avoidPositions?: Set<string>
): DirectionKey | null {
  const head = cpuSnake[0];
  const headKey = getCpuPositionKey(head);
  const dirs: DirectionKey[] = ['UP', 'DOWN', 'LEFT', 'RIGHT'];

  
  for (const dir of dirs) {
    const d = DIRECTION[dir];
    const nx = head.x + d.x;
    const nz = head.z + d.z;
    const wrap = applyWrap(nx, nz, gridSize, openSides);
    if (wrap.hitWall) continue;
    const key = `${wrap.x},${wrap.z}`;
    
    
    if (wrap.x === food.x && wrap.z === food.z) return dir;
  }

  
  const obstacleSet = buildObstacleSet(cpuSnake, playerSnake, wallSet, bug);

  
  type BfsNode = { x: number; z: number; firstDir: DirectionKey };
  const visited = new Set<string>();
  visited.add(headKey);
  const queue: BfsNode[] = [];

  
  for (const dir of dirs) {
    const d = DIRECTION[dir];
    const result = isNavigable(head.x + d.x, head.z + d.z, gridSize, openSides, obstacleSet, visited);
    if (!result.ok) continue;
    
    if (avoidPositions && avoidPositions.has(`${result.wx},${result.wz}`)) continue;
    visited.add(`${result.wx},${result.wz}`);
    if (result.wx === food.x && result.wz === food.z) return dir;
    queue.push({ x: result.wx, z: result.wz, firstDir: dir });
  }

  
  if (queue.length === 0 && avoidPositions) {
    for (const dir of dirs) {
      const d = DIRECTION[dir];
      const result = isNavigable(head.x + d.x, head.z + d.z, gridSize, openSides, obstacleSet, visited);
      if (!result.ok) continue;
      visited.add(`${result.wx},${result.wz}`);
      if (result.wx === food.x && result.wz === food.z) return dir;
      queue.push({ x: result.wx, z: result.wz, firstDir: dir });
    }
  }

  let explored = 0;
  while (queue.length > 0 && explored < CPU_BFS_LIMIT) {
    const node = queue.shift()!;
    explored++;

    for (const dir of dirs) {
      const d = DIRECTION[dir];
      const result = isNavigable(node.x + d.x, node.z + d.z, gridSize, openSides, obstacleSet, visited);
      if (!result.ok) continue;
      visited.add(`${result.wx},${result.wz}`);
      if (result.wx === food.x && result.wz === food.z) return node.firstDir;
      queue.push({ x: result.wx, z: result.wz, firstDir: node.firstDir });
    }
  }

  return null; 
}

function detectOscillation(head: Position): { isStuck: boolean; recentSet: Set<string> } {
  const recentSet = new Set<string>();
  for (const pos of cpuRecentPositions) {
    recentSet.add(getCpuPositionKey(pos));
  }
  
  let samePosCount = 0;
  for (const pos of cpuRecentPositions) {
    if (pos.x === head.x && pos.z === head.z) samePosCount++;
  }
  
  let isStuck = samePosCount >= 2;
  if (!isStuck && cpuRecentPositions.length >= 4) {
    const len = cpuRecentPositions.length;
    const p1 = cpuRecentPositions[len - 1];
    const p2 = cpuRecentPositions[len - 2];
    const p3 = cpuRecentPositions[len - 3];
    const p4 = cpuRecentPositions[len - 4];
    if (p1.x === p3.x && p1.z === p3.z && p2.x === p4.x && p2.z === p4.z) {
      isStuck = true;
    }
  }
  return { isStuck, recentSet };
}

function getCpuDirection(
  cpuSnake: Position[],
  food: Position,
  wallSet: Set<string>,
  playerSnake: Position[],
  gridSize: number,
  openSides: OpenSides,
  bug: Position | null
): DirectionKey {
  const head = cpuSnake[0];
  const dirs: DirectionKey[] = ['UP', 'DOWN', 'LEFT', 'RIGHT'];

  
  const { isStuck, recentSet } = detectOscillation(head);

  
  
  const avoidPositions = isStuck ? recentSet : undefined;
  const bfsDir = bfsPathToFood(cpuSnake, food, wallSet, playerSnake, gridSize, openSides, bug, avoidPositions);
  if (bfsDir) {
    
    cpuRecentPositions.push({ x: head.x, z: head.z });
    if (cpuRecentPositions.length > CPU_POSITION_HISTORY) {
      cpuRecentPositions.shift();
    }
    return bfsDir;
  }

  
  

  
  const obstacleSet = buildObstacleSet(cpuSnake, playerSnake, wallSet, bug);
  const safeDirs = dirs.filter(dir => {
    const d = DIRECTION[dir];
    const nx = head.x + d.x;
    const nz = head.z + d.z;
    const wrap = applyWrap(nx, nz, gridSize, openSides);
    if (wrap.hitWall) return false;
    const key = `${wrap.x},${wrap.z}`;
    return !obstacleSet.has(key);
  });

  if (safeDirs.length === 0) return dirs[0]; 

  
  let candidateDirs = safeDirs;
  if (isStuck || cpuRecentPositions.length >= 4) {
    const nonRecentDirs = safeDirs.filter(dir => {
      const d = DIRECTION[dir];
      const nx = head.x + d.x;
      const nz = head.z + d.z;
      const wrap = applyWrap(nx, nz, gridSize, openSides);
      return !recentSet.has(`${wrap.x},${wrap.z}`);
    });
    if (nonRecentDirs.length > 0) {
      candidateDirs = nonRecentDirs;
    }
  }

  
  
  let bestDir = candidateDirs[0];
  let bestScore = -1;

  for (const dir of candidateDirs) {
    const d = DIRECTION[dir];
    const nx = head.x + d.x;
    const nz = head.z + d.z;
    const wrap = applyWrap(nx, nz, gridSize, openSides);
    if (wrap.hitWall) continue;

    
    const floodVisited = new Set<string>();
    const floodQueue: Position[] = [{ x: wrap.x, z: wrap.z }];
    floodVisited.add(`${wrap.x},${wrap.z}`);
    let floodCount = 0;
    const floodLimit = 50;

    while (floodQueue.length > 0 && floodCount < floodLimit) {
      const curr = floodQueue.shift()!;
      floodCount++;

      for (const fDir of dirs) {
        const fd = DIRECTION[fDir];
        const fx = curr.x + fd.x;
        const fz = curr.z + fd.z;
        const fWrap = applyWrap(fx, fz, gridSize, openSides);
        if (fWrap.hitWall) continue;
        const fKey = `${fWrap.x},${fWrap.z}`;
        if (obstacleSet.has(fKey) || floodVisited.has(fKey)) continue;
        floodVisited.add(fKey);
        floodQueue.push({ x: fWrap.x, z: fWrap.z });
      }
    }

    
    const dx = Math.min(Math.abs(wrap.x - food.x), gridSize - Math.abs(wrap.x - food.x));
    const dz = Math.min(Math.abs(wrap.z - food.z), gridSize - Math.abs(wrap.z - food.z));
    const foodDist = dx + dz;
    const score = floodCount * 10 - foodDist;

    if (score > bestScore) {
      bestScore = score;
      bestDir = dir;
    }
  }

  
  cpuRecentPositions.push({ x: head.x, z: head.z });
  if (cpuRecentPositions.length > CPU_POSITION_HISTORY) {
    cpuRecentPositions.shift();
  }

  return bestDir;
}

function clearCpuMemory() {
  cpuRecentPositions.length = 0;
}

const BUG_MOVE_INTERVAL = 3; 

function moveBug(
  bug: Position,
  bugPrevPos: Position | null,
  food: Position,
  wallSet: Set<string>,
  playerSnake: Position[],
  cpuSnake: Position[],
  gridSize: number,
  openSides: OpenSides
): { newBug: Position; newFood: Position; bugMoved: boolean } {
  const dirs: DirectionKey[] = ['UP', 'DOWN', 'LEFT', 'RIGHT'];
  const head = bug;

  
  const safeDirs = dirs.filter(dir => {
    const d = DIRECTION[dir];
    let nx = head.x + d.x;
    let nz = head.z + d.z;
    const wrap = applyWrap(nx, nz, gridSize, openSides);
    if (wrap.hitWall) return false;
    nx = wrap.x;
    nz = wrap.z;
    if (wallSet.has(`${nx},${nz}`)) return false;
    
    for (let i = 1; i < playerSnake.length; i++) {
      if (playerSnake[i].x === nx && playerSnake[i].z === nz) return false;
    }
    return true;
  });

  if (safeDirs.length === 0) {
    return { newBug: bug, newFood: food, bugMoved: false };
  }

  
  const nonReverseDirs = safeDirs.filter(dir => {
    if (!bugPrevPos) return true;
    const d = DIRECTION[dir];
    let nx = head.x + d.x;
    let nz = head.z + d.z;
    const wrap = applyWrap(nx, nz, gridSize, openSides);
    nx = wrap.x;
    nz = wrap.z;
    
    return nx !== bugPrevPos.x || nz !== bugPrevPos.z;
  });

  
  const candidateDirs = nonReverseDirs.length > 0 ? nonReverseDirs : safeDirs;

  
  let bestDir = candidateDirs[0];
  let bestDist = Infinity;
  for (const dir of candidateDirs) {
    const d = DIRECTION[dir];
    let nx = head.x + d.x;
    let nz = head.z + d.z;
    const wrap = applyWrap(nx, nz, gridSize, openSides);
    nx = wrap.x;
    nz = wrap.z;
    const dx = Math.min(Math.abs(nx - food.x), gridSize - Math.abs(nx - food.x));
    const dz = Math.min(Math.abs(nz - food.z), gridSize - Math.abs(nz - food.z));
    const dist = dx + dz;
    if (dist < bestDist) {
      bestDist = dist;
      bestDir = dir;
    }
  }

  const bd = DIRECTION[bestDir];
  let newBugX = head.x + bd.x;
  let newBugZ = head.z + bd.z;
  const bugWrap = applyWrap(newBugX, newBugZ, gridSize, openSides);
  newBugX = bugWrap.x;
  newBugZ = bugWrap.z;

  const newBug = { x: newBugX, z: newBugZ };
  let newFood = food;

  
  if (newBug.x === food.x && newBug.z === food.z) {
    
    let pushX = food.x + bd.x;
    let pushZ = food.z + bd.z;
    const pushWrap = applyWrap(pushX, pushZ, gridSize, openSides);

    if (!pushWrap.hitWall) {
      pushX = pushWrap.x;
      pushZ = pushWrap.z;
      const pushKey = `${pushX},${pushZ}`;
      const pushBlocked = wallSet.has(pushKey) ||
        playerSnake.some(s => s.x === pushX && s.z === pushZ) ||
        cpuSnake.some(s => s.x === pushX && s.z === pushZ);

      if (!pushBlocked) {
        newFood = { x: pushX, z: pushZ };
        return { newBug, newFood, bugMoved: true };
      }
    }

    
    const perpDirs: DirectionKey[] = bestDir === 'UP' || bestDir === 'DOWN'
      ? ['LEFT', 'RIGHT'] : ['UP', 'DOWN'];

    for (const pd of perpDirs) {
      const pdd = DIRECTION[pd];
      let altX = food.x + pdd.x;
      let altZ = food.z + pdd.z;
      const altWrap = applyWrap(altX, altZ, gridSize, openSides);

      if (!altWrap.hitWall) {
        altX = altWrap.x;
        altZ = altWrap.z;
        const altKey = `${altX},${altZ}`;
        const altBlocked = wallSet.has(altKey) ||
          playerSnake.some(s => s.x === altX && s.z === altZ) ||
          cpuSnake.some(s => s.x === altX && s.z === altZ);

        if (!altBlocked) {
          newFood = { x: altX, z: altZ };
          return { newBug, newFood, bugMoved: true };
        }
      }
    }

    
    return { newBug: bug, newFood: food, bugMoved: false };
  }

  return { newBug, newFood, bugMoved: true };
}

export const useGameStore = create<GameState>((set, get) => ({
  mode: 'classic',
  mapConfig: null,
  gridSize: CLASSIC_GRID_SIZE,
  wallSet: new Set<string>(),
  openSides: { ...NO_OPEN_SIDES },

  snake: [...INITIAL_SNAKE],
  prevSnake: [...INITIAL_SNAKE],
  direction: 'RIGHT',
  nextDirection: 'RIGHT',

  cpuSnake: [],
  prevCpuSnake: [],
  cpuDirection: 'RIGHT',
  cpuScore: 0,
  cpuAlive: false,

  bug: null,
  bugPrevPos: null,
  bugTickCount: 0,
  bugMoveAccum: 0,

  hasLamps: false,
  hasFireflies: false,

  timeMode: 'cycle' as TimeMode,
  customTimeHour: 12,
  customTimeMinute: 0,
  cloudsEnabled: true,
  shadowMode: 'dynamic' as ShadowMode,
  fixedShadowAngle: 45,
  lampColor: 'yellow' as LampColorMode,
  masterVolume: 100,

  food: { x: 15, z: 15 },
  score: 0,
  highScore: loadHighScore(),

  status: 'menu',
  speed: INITIAL_SPEED,
  baseSpeed: INITIAL_SPEED,
  playerMoveAccum: 0,
  cpuMoveAccum: 0,

  foodPowerUp: 'none' as PowerUpType,
  foodSpawnTime: 0,
  immortalEnd: 0,
  speedBoostEnd: 0,
  slowEnd: 0,
  cpuImmortalEnd: 0,
  cpuSpeedBoostEnd: 0,
  cpuSlowEnd: 0,

  particles: [],
  lastParticleId: 0,
  eatAnimation: 0,
  shakeIntensity: 0,
  gameResult: null,
  bugHitTime: 0,
  lastTickTime: 0,
  lastPlayerMoveTime: 0,
  lastCpuMoveTime: 0,

  setMode: (mode: MapMode) => {
    set({ mode });
  },

  setTimeMode: (mode: TimeMode) => {
    set({ timeMode: mode });
  },

  setCustomTime: (hour: number, minute: number) => {
    set({ customTimeHour: hour, customTimeMinute: minute });
  },

  setCloudsEnabled: (enabled: boolean) => {
    set({ cloudsEnabled: enabled });
  },

  setShadowMode: (mode: ShadowMode) => {
    set({ shadowMode: mode });
  },

  setFixedShadowAngle: (angle: number) => {
    set({ fixedShadowAngle: angle });
  },

  setLampColor: (color: LampColorMode) => {
    set({ lampColor: color });
  },

  setMasterVolume: (volume: number) => {
    const clamped = Math.max(0, Math.min(100, volume));
    set({ masterVolume: clamped });
    
    const { setMasterVolume: setAudioVolume } = require('./sounds');
    setAudioVolume(clamped / 100);
  },

  startGame: () => {
    const state = get();
    const mode = state.mode;
    clearCpuMemory();

    let gridSize: number;
    let wallSet: Set<string>;
    let openSides: OpenSides;
    let mapConfig: MapConfig | null = null;
    let cpuSnake: Position[] = [];
    let cpuAlive = false;
    let bug: Position | null = null;
    let snake: Position[];

    if (mode === 'arcade') {
      mapConfig = generateArcadeMap();
      gridSize = mapConfig.gridSize;
      wallSet = new Set(mapConfig.walls.map(w => posKey(w)));
      openSides = mapConfig.openSides;

      
      const cx = Math.floor(gridSize / 2);
      const cz = Math.floor(gridSize / 2);
      snake = [
        { x: cx, z: cz },
        { x: cx - 1, z: cz },
        { x: cx - 2, z: cz },
      ];

      if (mapConfig.hasCpuSnake) {
        cpuSnake = [
          { x: 2, z: 2 },
          { x: 3, z: 2 },
          { x: 4, z: 2 },
        ];
        cpuAlive = true;
      }

      if (mapConfig.hasBug) {
        const occ = getOccupiedSet(snake, cpuSnake, mapConfig.walls, null, { x: -1, z: -1 });
        bug = randomFoodPosition(gridSize, occ);
      }
    } else {
      gridSize = CLASSIC_GRID_SIZE;
      wallSet = new Set<string>();
      openSides = { ...NO_OPEN_SIDES };
      snake = [...INITIAL_SNAKE];
    }

    
    const occ = getOccupiedSet(snake, cpuSnake, mapConfig?.walls || [], bug, { x: -1, z: -1 });
    const food = randomFoodPosition(gridSize, occ);

    set({
      mapConfig,
      gridSize,
      wallSet,
      openSides,
      snake,
      prevSnake: snake.map(s => ({ ...s })),
      direction: 'RIGHT',
      nextDirection: 'RIGHT',
      cpuSnake,
      prevCpuSnake: cpuSnake.map(s => ({ ...s })),
      cpuDirection: 'RIGHT',
      cpuScore: 0,
      cpuAlive,
      bug,
      food,
      score: 0,
      status: 'playing',
      speed: INITIAL_SPEED,
      baseSpeed: INITIAL_SPEED,
      playerMoveAccum: 0,
      cpuMoveAccum: 0,
      particles: [],
      eatAnimation: 0,
      shakeIntensity: 0,
      gameResult: null,
      bugHitTime: 0,
      lastTickTime: Date.now(),
      lastPlayerMoveTime: Date.now(),
      lastCpuMoveTime: Date.now(),
      bugPrevPos: null,
      bugTickCount: 0,
      bugMoveAccum: 0,
      hasLamps: mode === 'arcade' ? (mapConfig?.hasLamps ?? false) : false,
      hasFireflies: mode === 'arcade' ? (mapConfig?.hasFireflies ?? false) : true,
      foodPowerUp: 'none',
      foodSpawnTime: Date.now(),
      immortalEnd: 0,
      speedBoostEnd: 0,
      slowEnd: 0,
      cpuImmortalEnd: 0,
      cpuSpeedBoostEnd: 0,
      cpuSlowEnd: 0,
    });
  },

  goToMenu: () => {
    set({ status: 'menu' });
  },

  pauseGame: () => {
    if (get().status === 'playing') set({ status: 'paused' });
  },

  resumeGame: () => {
    if (get().status === 'paused') set({ status: 'playing' });
  },

  setDirection: (dir: DirectionKey) => {
    const state = get();
    if (state.status !== 'playing') return;
    if (OPPOSITE[dir] === state.direction) return;
    set({ nextDirection: dir });
  },

  tick: () => {
    const state = get();
    if (state.status !== 'playing') return;

    const { gridSize, wallSet, openSides, bug } = state;

    
    
    
    
    const now = Date.now();
    const playerHasBoost = state.speedBoostEnd > 0 && now < state.speedBoostEnd;
    const playerIsSlowed = state.slowEnd > 0 && now < state.slowEnd;
    const cpuHasBoost = state.cpuSpeedBoostEnd > 0 && now < state.cpuSpeedBoostEnd;
    const cpuIsSlowed = state.cpuSlowEnd > 0 && now < state.cpuSlowEnd;
    
    let playerInterval = state.baseSpeed;
    if (playerHasBoost) playerInterval /= SPEED_BOOST_MULTIPLIER;
    if (playerIsSlowed) playerInterval *= SLOW_MULTIPLIER;
    let cpuInterval = state.baseSpeed;
    if (cpuHasBoost) cpuInterval /= SPEED_BOOST_MULTIPLIER;
    if (cpuIsSlowed) cpuInterval *= SLOW_MULTIPLIER;

    
    const tickDelta = state.speed;
    let newPlayerMoveAccum = state.playerMoveAccum + tickDelta;
    let newCpuMoveAccum = state.cpuMoveAccum + tickDelta;

    const shouldMovePlayer = newPlayerMoveAccum >= playerInterval;
    const shouldMoveCpu = state.cpuAlive && state.cpuSnake.length > 0 && newCpuMoveAccum >= cpuInterval;

    if (shouldMovePlayer) newPlayerMoveAccum -= playerInterval;
    if (shouldMoveCpu) newCpuMoveAccum -= cpuInterval;

    
    let currentFoodPowerUp = state.foodPowerUp;
    let currentFoodSpawnTime = state.foodSpawnTime;
    if (currentFoodPowerUp !== 'none' && currentFoodSpawnTime > 0) {
      if (Date.now() - currentFoodSpawnTime >= POWERUP_EXPIRY) {
        currentFoodPowerUp = 'none';
      }
    }

    
    let newPlayerSnake = [...state.snake];
    
    const prevSnake = shouldMovePlayer ? state.snake.map(s => ({ ...s })) : state.prevSnake;
    let playerDir = state.direction; 
    let willPlayerEat = false;
    let bugHitPlayer = false;
    let playerDiedBlack = false;
    const playerIsImmortal = state.immortalEnd > 0 && now < state.immortalEnd;
    const cpuIsImmortal = state.cpuImmortalEnd > 0 && now < state.cpuImmortalEnd;
    let newLastPlayerMoveTime = shouldMovePlayer ? Date.now() : state.lastPlayerMoveTime;
    let newLastCpuMoveTime = state.lastCpuMoveTime;

    if (shouldMovePlayer) {
      playerDir = state.nextDirection;
      const playerD = DIRECTION[playerDir];
      const playerHead = state.snake[0];
      let newPX = playerHead.x + playerD.x;
      let newPZ = playerHead.z + playerD.z;

      
      const playerWrap = applyWrap(newPX, newPZ, gridSize, openSides);
      if (playerWrap.hitWall) {
        if (!playerIsImmortal) {
          const highScore = Math.max(state.score, state.highScore);
          saveHighScore(highScore);
          const result = state.cpuAlive ? (state.score > state.cpuScore ? 'won' : state.score < state.cpuScore ? 'lost' : 'tied') : null;
          set({ status: 'gameover', highScore, shakeIntensity: 1, gameResult: result });
          return;
        }
        
        newPX = playerHead.x;
        newPZ = playerHead.z;
      }
      newPX = playerWrap.hitWall ? playerHead.x : playerWrap.x;
      newPZ = playerWrap.hitWall ? playerHead.z : playerWrap.z;

      
      if (wallSet.has(`${newPX},${newPZ}`) && !playerIsImmortal) {
        const highScore = Math.max(state.score, state.highScore);
        saveHighScore(highScore);
        const result = state.cpuAlive ? (state.score > state.cpuScore ? 'won' : state.score < state.cpuScore ? 'lost' : 'tied') : null;
        set({ status: 'gameover', highScore, shakeIntensity: 1, gameResult: result });
        return;
      }

      
      if (!playerIsImmortal) {
        const playerBodyCheck = state.snake.slice(0, -1);
        if (playerBodyCheck.some(s => s.x === newPX && s.z === newPZ)) {
          const highScore = Math.max(state.score, state.highScore);
          saveHighScore(highScore);
          const result = state.cpuAlive ? (state.score > state.cpuScore ? 'won' : state.score < state.cpuScore ? 'lost' : 'tied') : null;
          set({ status: 'gameover', highScore, shakeIntensity: 1, gameResult: result });
          return;
        }
      }

      
      if (state.cpuAlive && state.cpuSnake.some(s => s.x === newPX && s.z === newPZ)) {
        if (!playerIsImmortal) {
          const highScore = Math.max(state.score, state.highScore);
          saveHighScore(highScore);
          const result = state.score > state.cpuScore ? 'won' : state.score < state.cpuScore ? 'lost' : 'tied';
          set({ status: 'gameover', highScore, shakeIntensity: 1, gameResult: result });
          return;
        }
      }

      
      willPlayerEat = newPX === state.food.x && newPZ === state.food.z;

      newPlayerSnake = [{ x: newPX, z: newPZ }, ...state.snake];
      if (!willPlayerEat) newPlayerSnake.pop();

      
      if (bug && newPX === bug.x && newPZ === bug.z && !playerIsImmortal) {
        bugHitPlayer = true;
        if (newPlayerSnake.length <= BUG_PENALTY_LENGTH) {
          const highScore = Math.max(state.score, state.highScore);
          saveHighScore(highScore);
          const result = state.cpuAlive ? 'lost' : null;
          set({ status: 'gameover', highScore, shakeIntensity: 1, gameResult: result });
          return;
        }
        newPlayerSnake.splice(newPlayerSnake.length - BUG_PENALTY_LENGTH, BUG_PENALTY_LENGTH);
      }
    }

    
    let newCpuSnake = [...state.cpuSnake];
    const prevCpuSnake = shouldMoveCpu ? state.cpuSnake.map(s => ({ ...s })) : state.prevCpuSnake;
    let cpuDied = false;
    let cpuAte = false;

    if (shouldMoveCpu) {
      newLastCpuMoveTime = Date.now();
      const cpuHead = newCpuSnake[0];
      let cpuDir = getCpuDirection(newCpuSnake, state.food, wallSet, newPlayerSnake, gridSize, openSides, bug);
      
      if (newCpuSnake.length > 1) {
        const prevHead = newCpuSnake[1]; 
        const cpuDCheck = DIRECTION[cpuDir];
        const nextX = cpuHead.x + cpuDCheck.x;
        const nextZ = cpuHead.z + cpuDCheck.z;
        
        if (nextX === prevHead.x && nextZ === prevHead.z) {
          const obstacleSet = buildObstacleSet(newCpuSnake, newPlayerSnake, wallSet, bug);
          const altDirs: DirectionKey[] = (['UP', 'DOWN', 'LEFT', 'RIGHT'] as DirectionKey[]).filter(d => {
            if (d === cpuDir) return false;
            const dd = DIRECTION[d];
            const nx = cpuHead.x + dd.x;
            const nz = cpuHead.z + dd.z;
            const w = applyWrap(nx, nz, gridSize, openSides);
            if (w.hitWall) return false;
            return !obstacleSet.has(`${w.x},${w.z}`);
          });
          if (altDirs.length > 0) cpuDir = altDirs[0];
        }
      }
      const cpuD = DIRECTION[cpuDir];
      let newCX = cpuHead.x + cpuD.x;
      let newCZ = cpuHead.z + cpuD.z;

      const cpuWrap = applyWrap(newCX, newCZ, gridSize, openSides);
      if (cpuWrap.hitWall) {
        if (!cpuIsImmortal) {
          cpuDied = true;
        } else {
          
          newCX = cpuHead.x;
          newCZ = cpuHead.z;
          newCpuSnake = [{ x: newCX, z: newCZ }, ...newCpuSnake];
          newCpuSnake.pop();
        }
      } else {
        newCX = cpuWrap.x;
        newCZ = cpuWrap.z;

        const cpuHitInterior = wallSet.has(`${newCX},${newCZ}`);
        const cpuEat = newCX === state.food.x && newCZ === state.food.z;
        const cpuBodyCheck = cpuEat ? newCpuSnake : newCpuSnake.slice(0, -1);
        const cpuSelfHit = !cpuIsImmortal && cpuBodyCheck.some(s => s.x === newCX && s.z === newCZ);
        const cpuPlayerHit = !cpuIsImmortal && newPlayerSnake.some(s => s.x === newCX && s.z === newCZ);

        if ((cpuHitInterior && !cpuIsImmortal) || cpuSelfHit || cpuPlayerHit) {
          cpuDied = true;
        } else {
          newCpuSnake = [{ x: newCX, z: newCZ }, ...newCpuSnake];
          if (cpuEat) {
            cpuAte = true;
          } else {
            newCpuSnake.pop();
          }
        }
      }
    }

    
    let newFood = state.food;
    let playerAte = false;
    let cpuJustAte = false;
    let newFoodPowerUp: PowerUpType = currentFoodPowerUp;
    let newFoodSpawnTime = currentFoodSpawnTime;
    let newImmortalEnd = state.immortalEnd;
    let newSpeedBoostEnd = state.speedBoostEnd;
    let newSlowEnd = state.slowEnd;
    let newCpuImmortalEnd = state.cpuImmortalEnd;
    let newCpuSpeedBoostEnd = state.cpuSpeedBoostEnd;
    let newCpuSlowEnd = state.cpuSlowEnd;

    if (willPlayerEat) {
      playerAte = true;
      const pu = currentFoodPowerUp;
      if (pu === 'golden') {
        
      } else if (pu === 'immortal') {
        newImmortalEnd = Date.now() + IMMORTAL_DURATION;
      } else if (pu === 'growth') {
        const tail = newPlayerSnake[newPlayerSnake.length - 1];
        newPlayerSnake.push({ ...tail }, { ...tail }, { ...tail });
      } else if (pu === 'speed') {
        newSpeedBoostEnd = Date.now() + SPEED_BOOST_DURATION;
      } else if (pu === 'slow') {
        newSlowEnd = Date.now() + SLOW_DURATION;
      } else if (pu === 'black') {
        if (newPlayerSnake.length <= BLACK_APPLE_LENGTH_PENALTY) {
          playerDiedBlack = true;
        } else {
          newPlayerSnake.splice(newPlayerSnake.length - BLACK_APPLE_LENGTH_PENALTY, BLACK_APPLE_LENGTH_PENALTY);
        }
      }
    } else if (cpuAte) {
      cpuJustAte = true;
      const pu = currentFoodPowerUp;
      if (pu === 'golden') {
        
      } else if (pu === 'immortal') {
        newCpuImmortalEnd = Date.now() + IMMORTAL_DURATION;
      } else if (pu === 'growth') {
        const tail = newCpuSnake[newCpuSnake.length - 1];
        newCpuSnake.push({ ...tail }, { ...tail }, { ...tail });
      } else if (pu === 'speed') {
        newCpuSpeedBoostEnd = Date.now() + SPEED_BOOST_DURATION;
      } else if (pu === 'slow') {
        newCpuSlowEnd = Date.now() + SLOW_DURATION;
      } else if (pu === 'black') {
        if (newCpuSnake.length <= BLACK_APPLE_LENGTH_PENALTY) {
          cpuDied = true;
        } else {
          newCpuSnake.splice(newCpuSnake.length - BLACK_APPLE_LENGTH_PENALTY, BLACK_APPLE_LENGTH_PENALTY);
        }
      }
    }

    
    if (playerDiedBlack) {
      const highScore = Math.max(state.score, state.highScore);
      saveHighScore(highScore);
      const result = state.cpuAlive ? 'lost' : null;
      set({ status: 'gameover', highScore, shakeIntensity: 1, gameResult: result });
      return;
    }

    
    if (newSpeedBoostEnd > 0 && now >= newSpeedBoostEnd) {
      newSpeedBoostEnd = 0;
    }
    
    if (newCpuSpeedBoostEnd > 0 && now >= newCpuSpeedBoostEnd) {
      newCpuSpeedBoostEnd = 0;
    }
    
    if (newSlowEnd > 0 && now >= newSlowEnd) {
      newSlowEnd = 0;
    }
    
    if (newCpuSlowEnd > 0 && now >= newCpuSlowEnd) {
      newCpuSlowEnd = 0;
    }
    
    if (newImmortalEnd > 0 && now >= newImmortalEnd) {
      newImmortalEnd = 0;
    }
    
    if (newCpuImmortalEnd > 0 && now >= newCpuImmortalEnd) {
      newCpuImmortalEnd = 0;
    }

    
    if (playerAte || cpuJustAte) {
      const occ = getOccupiedSet(
        newPlayerSnake,
        cpuDied ? [] : newCpuSnake,
        state.mapConfig?.walls || [],
        bug,
        { x: -1, z: -1 }
      );
      newFood = randomFoodPosition(gridSize, occ);
      newFoodPowerUp = state.mode === 'arcade' ? rollPowerUp() : 'none';
      newFoodSpawnTime = Date.now();
    }

    
    let newBug = bug ? { ...bug } : null;
    let newBugPrevPos = state.bugPrevPos;
    let newBugMoveAccum = state.bugMoveAccum + tickDelta;
    const bugMoveInterval = state.baseSpeed * BUG_MOVE_INTERVAL;

    if (bug && state.mapConfig?.hasBug && newBugMoveAccum >= bugMoveInterval) {
      newBugMoveAccum -= bugMoveInterval;
      const result = moveBug(
        bug, state.bugPrevPos, newFood, wallSet, newPlayerSnake,
        cpuDied ? [] : newCpuSnake,
        gridSize, openSides
      );
      if (result.bugMoved) {
        newBugPrevPos = { ...bug };
        newBug = result.newBug;
        newFood = result.newFood;
      }
    }

    
    const goldenExtra = (playerAte && currentFoodPowerUp === 'golden') ? 2 : 0;
    const cpuGoldenExtra = (cpuJustAte && currentFoodPowerUp === 'golden') ? 2 : 0;
    const newScore = (playerAte ? state.score + 1 : state.score) + goldenExtra - (bugHitPlayer ? BUG_PENALTY_SCORE : 0);
    const finalScore = Math.max(0, newScore);
    const newCpuScore = cpuJustAte ? state.cpuScore + 1 + cpuGoldenExtra : state.cpuScore;

    
    let newBaseSpeed = (playerAte || cpuJustAte)
      ? Math.max(MIN_SPEED, state.baseSpeed - SPEED_DECREASE)
      : state.baseSpeed;

    
    const newPlayerHasBoost = newSpeedBoostEnd > 0 && now < newSpeedBoostEnd;
    const newPlayerIsSlowed = newSlowEnd > 0 && now < newSlowEnd;
    const newCpuHasBoost = newCpuSpeedBoostEnd > 0 && now < newCpuSpeedBoostEnd;
    const newCpuIsSlowed = newCpuSlowEnd > 0 && now < newCpuSlowEnd;
    let newPlayerInterval = newBaseSpeed;
    if (newPlayerHasBoost) newPlayerInterval /= SPEED_BOOST_MULTIPLIER;
    if (newPlayerIsSlowed) newPlayerInterval *= SLOW_MULTIPLIER;
    let newCpuInterval = newBaseSpeed;
    if (newCpuHasBoost) newCpuInterval /= SPEED_BOOST_MULTIPLIER;
    if (newCpuIsSlowed) newCpuInterval *= SLOW_MULTIPLIER;

    
    
    let effectiveSpeed: number;
    if (state.cpuAlive && !cpuDied) {
      effectiveSpeed = Math.min(newPlayerInterval, newCpuInterval);
    } else {
      effectiveSpeed = newPlayerInterval;
    }
    effectiveSpeed = Math.max(MIN_SPEED / SPEED_BOOST_MULTIPLIER, effectiveSpeed);

    const highScore = Math.max(finalScore, state.highScore);
    if (finalScore > state.highScore) saveHighScore(finalScore);

    set({
      snake: newPlayerSnake,
      prevSnake,
      direction: playerDir,
      food: newFood,
      score: finalScore,
      highScore,
      speed: effectiveSpeed,
      baseSpeed: newBaseSpeed,
      playerMoveAccum: newPlayerMoveAccum,
      cpuMoveAccum: newCpuMoveAccum,
      cpuSnake: cpuDied ? [] : newCpuSnake,
      prevCpuSnake,
      cpuDirection: state.cpuAlive && !cpuDied ? state.cpuDirection : state.cpuDirection,
      cpuScore: newCpuScore,
      cpuAlive: state.cpuAlive && !cpuDied,
      bug: state.mapConfig?.hasBug ? newBug : null,
      bugPrevPos: newBugPrevPos,
      bugMoveAccum: newBugMoveAccum,
      lastTickTime: Date.now(),
      lastPlayerMoveTime: newLastPlayerMoveTime,
      lastCpuMoveTime: newLastCpuMoveTime,
      foodPowerUp: newFoodPowerUp,
      foodSpawnTime: newFoodSpawnTime,
      immortalEnd: newImmortalEnd,
      speedBoostEnd: newSpeedBoostEnd,
      slowEnd: newSlowEnd,
      cpuImmortalEnd: newCpuImmortalEnd,
      cpuSpeedBoostEnd: newCpuSpeedBoostEnd,
      cpuSlowEnd: newCpuSlowEnd,
      ...(playerAte ? { eatAnimation: Date.now() } : {}),
      ...(bugHitPlayer ? { bugHitTime: Date.now(), shakeIntensity: 0.6 } : {}),
    });
  },

  spawnParticles: (x: number, z: number) => {
    const state = get();
    const newParticles: Particle[] = [];
    for (let i = 0; i < 12; i++) {
      const angle = (Math.PI * 2 * i) / 12 + Math.random() * 0.5;
      const speed = 2 + Math.random() * 3;
      newParticles.push({
        id: state.lastParticleId + i + 1,
        x, z,
        vx: Math.cos(angle) * speed,
        vz: Math.sin(angle) * speed,
        life: 1,
      });
    }
    set({
      particles: [...state.particles, ...newParticles],
      lastParticleId: state.lastParticleId + 12,
    });
  },

  updateParticles: (dt: number) => {
    const state = get();
    const updated = state.particles
      .map(p => ({
        ...p,
        x: p.x + p.vx * dt,
        z: p.z + p.vz * dt,
        life: p.life - dt * 2,
      }))
      .filter(p => p.life > 0);
    set({ particles: updated });
  },
}));
