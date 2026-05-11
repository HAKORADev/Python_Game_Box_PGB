'use client';

import React, { useEffect, useCallback, useRef, useState } from 'react';
import { useGameStore } from '@/game/store';
import { DirectionKey, gridToWorld, getGameHour, TimeMode, ShadowMode, LampColorMode, PowerUpType, SPEED_BOOST_DURATION, POWERUP_EXPIRY } from '@/game/constants';
import { playEatSound, playGameOverSound, playMoveSound, playStartSound, playBugHitSound, startAmbientSound, stopAmbientSound, playPowerUpSound } from '@/game/sounds';
import { CYCLE_SECONDS } from '@/game/constants';

function formatGameTime(hour: number): string {
  const h = Math.floor(hour) % 24;
  const m = Math.floor((hour % 1) * 60);
  const period = h >= 12 ? 'PM' : 'AM';
  const displayH = h === 0 ? 12 : h > 12 ? h - 12 : h;
  return `${displayH}:${m.toString().padStart(2, '0')} ${period}`;
}

function getTimeIcon(hour: number): string {
  if (hour >= 6 && hour < 18) return '☀️';
  if (hour >= 18 && hour < 20) return '🌅';
  if (hour >= 5 && hour < 6) return '🌄';
  return '🌙';
}

function TreeShadowDemo({ angle }: { angle: number }) {
  
  
  const rad = (angle * Math.PI) / 180;
  const shadowLen = 30;
  const endX = 50 + Math.cos(rad) * shadowLen;
  const endY = 55 + Math.sin(rad) * shadowLen;

  return (
    <div className="w-[100px] h-[100px] rounded-lg border border-white/10 relative overflow-hidden"
      style={{ background: 'linear-gradient(180deg, #87ceeb 0%, #b8d8f0 40%, #90c870 65%, #5a9e3a 100%)' }}>
      
      <div className="absolute bottom-0 left-0 right-0 h-[38%]"
        style={{ background: 'linear-gradient(180deg, #6aaa40 0%, #4a8a28 50%, #3a7a1c 100%)' }} />
      
      <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100">
        <line
          x1="50" y1="58" x2={endX} y2={endY}
          stroke="rgba(0,0,0,0.3)" strokeWidth="7" strokeLinecap="round"
        />
        
        <line
          x1="50" y1="58" x2={(50 + endX) / 2} y2={(55 + endY) / 2}
          stroke="rgba(0,0,0,0.15)" strokeWidth="10" strokeLinecap="round"
        />
      </svg>
      
      <div className="absolute left-[47px] top-[38px] w-[6px] h-[22px] rounded-sm"
        style={{ background: 'linear-gradient(90deg, #4a2e16 0%, #6b3a1f 50%, #4a2e16 100%)' }} />
      
      <div className="absolute left-[35px] top-[28px] w-[30px] h-[18px] rounded-[50%]"
        style={{ background: 'radial-gradient(ellipse at 50% 60%, #2d6b1e 0%, #1a4a10 80%)' }} />
      
      <div className="absolute left-[38px] top-[22px] w-[24px] h-[14px] rounded-[50%]"
        style={{ background: 'radial-gradient(ellipse at 50% 60%, #358524 0%, #1f5514 80%)' }} />
      
      <div className="absolute bottom-1 left-0 right-0 text-center text-[9px] text-white/70 font-medium drop-shadow-sm">
        {angle}°
      </div>
    </div>
  );
}

function LampPreview({ color }: { color: LampColorMode }) {
  const isYellow = color === 'yellow';
  const lightColor = isYellow ? '#ffcc66' : '#c8d8f0';
  const lightColorRGB = isYellow ? '255,204,102' : '200,216,240';

  return (
    <div className="w-[200px] h-[140px] rounded-lg border border-white/10 relative overflow-hidden"
      style={{ background: 'linear-gradient(180deg, #080c18 0%, #0a1020 40%, #0c1428 100%)' }}>
      
      <div className="absolute bottom-0 left-0 right-0 h-[35%]"
        style={{ background: 'linear-gradient(180deg, #1a2e14 0%, #152810 50%, #0f1e0c 100%)' }} />
      
      
      <div className="absolute top-[6px] left-[15px] w-[1px] h-[1px] rounded-full bg-white/60" />
      <div className="absolute top-[12px] left-[45px] w-[1px] h-[1px] rounded-full bg-white/40" />
      <div className="absolute top-[8px] right-[30px] w-[1px] h-[1px] rounded-full bg-white/50" />
      <div className="absolute top-[15px] right-[60px] w-[1px] h-[1px] rounded-full bg-white/30" />
      <div className="absolute top-[4px] right-[15px] w-[1px] h-[1px] rounded-full bg-white/60" />
      <div className="absolute top-[18px] left-[70px] w-[1px] h-[1px] rounded-full bg-white/40" />

      
      <div className="absolute left-1/2 -translate-x-1/2 bottom-[8px] w-[130px] h-[40px] rounded-full"
        style={{ background: `radial-gradient(ellipse at 50% 20%, rgba(${lightColorRGB},0.3) 0%, rgba(${lightColorRGB},0.08) 40%, transparent 80%)` }} />

      
      <div className="absolute left-1/2 -translate-x-1/2 bottom-[8px] w-[3px] h-[70px] rounded-sm"
        style={{ background: 'linear-gradient(180deg, #555 0%, #3a3a3a 100%)' }} />
      
      <div className="absolute left-1/2 -translate-x-1/2 bottom-[6px] w-[8px] h-[4px] rounded-sm bg-gray-600" />
      
      <div className="absolute left-1/2 -translate-x-1/2 bottom-[72px] w-[16px] h-[6px] rounded-t-md"
        style={{ background: 'linear-gradient(180deg, #4a4a4a 0%, #3a3a3a 100%)' }} />
      
      <div className="absolute left-1/2 -translate-x-1/2 bottom-[68px] w-[10px] h-[8px] rounded-full"
        style={{ backgroundColor: lightColor, boxShadow: `0 0 10px 4px rgba(${lightColorRGB},0.5), 0 0 20px 8px rgba(${lightColorRGB},0.15)` }} />

      
      <div className="absolute" style={{ left: '14px', bottom: '20px', width: '20px', height: '34px' }}>
        <div className="absolute top-[0px] left-[3px] w-[14px] h-[10px] rounded-[50%]"
          style={{ background: 'radial-gradient(ellipse at 60% 50%, #358524 0%, #1f5514 80%)' }} />
        <div className="absolute top-[6px] left-[1px] w-[18px] h-[13px] rounded-[50%]"
          style={{ background: 'radial-gradient(ellipse at 60% 50%, #2d6b1e 0%, #1a4a10 80%)' }} />
        <div className="absolute top-[16px] left-[8px] w-[3px] h-[18px]"
          style={{ background: 'linear-gradient(180deg, #5a3a1f 0%, #4a2e16 100%)' }} />
      </div>

      
      <div className="absolute" style={{ right: '14px', bottom: '22px', width: '22px', height: '36px' }}>
        <div className="absolute top-[0px] left-[4px] w-[15px] h-[11px] rounded-[50%]"
          style={{ background: 'radial-gradient(ellipse at 40% 50%, #358524 0%, #1f5514 80%)' }} />
        <div className="absolute top-[7px] left-[1px] w-[20px] h-[14px] rounded-[50%]"
          style={{ background: 'radial-gradient(ellipse at 40% 50%, #2d6b1e 0%, #1a4a10 80%)' }} />
        <div className="absolute top-[18px] left-[9px] w-[3px] h-[18px]"
          style={{ background: 'linear-gradient(180deg, #5a3a1f 0%, #4a2e16 100%)' }} />
      </div>

      
      <div className="absolute" style={{ left: '38px', bottom: '10px', width: '18px', height: '28px' }}>
        <div className="absolute top-[0px] left-[2px] w-[14px] h-[10px] rounded-[50%]"
          style={{ background: `radial-gradient(ellipse at 65% 40%, #3d952c 0%, #2d6b1e 60%), radial-gradient(ellipse at 65% 40%, rgba(${lightColorRGB},0.06) 0%, transparent 70%)` }} />
        <div className="absolute top-[14px] left-[7px] w-[4px] h-[14px]"
          style={{ background: 'linear-gradient(180deg, #5a3a1f 0%, #4a2e16 100%)' }} />
      </div>

      
      <div className="absolute" style={{ right: '38px', bottom: '10px', width: '16px', height: '26px' }}>
        <div className="absolute top-[0px] left-[1px] w-[14px] h-[9px] rounded-[50%]"
          style={{ background: `radial-gradient(ellipse at 35% 40%, #3d952c 0%, #2d6b1e 60%), radial-gradient(ellipse at 35% 40%, rgba(${lightColorRGB},0.06) 0%, transparent 70%)` }} />
        <div className="absolute top-[12px] left-[6px] w-[4px] h-[14px]"
          style={{ background: 'linear-gradient(180deg, #5a3a1f 0%, #4a2e16 100%)' }} />
      </div>

      
      <div className="absolute top-[3px] left-[5px] text-[8px] font-mono text-white/30">2:00 AM</div>
      
      
      <div className="absolute top-[3px] right-[5px] text-[8px] font-medium" style={{ color: lightColor }}>
        {isYellow ? 'Warm' : 'Cool LED'}
      </div>
    </div>
  );
}

export default function GameUI() {
  const {
    mode, mapConfig, score, highScore, status, speed, snake, food,
    direction, cpuScore, cpuAlive, bug, gridSize, gameResult, openSides,
    bugHitTime, hasLamps, hasFireflies, timeMode,
    cloudsEnabled, shadowMode, fixedShadowAngle, lampColor, customTimeHour, customTimeMinute,
    masterVolume,
    immortalEnd, speedBoostEnd, slowEnd, foodPowerUp, foodSpawnTime,
    cpuImmortalEnd, cpuSpeedBoostEnd, cpuSlowEnd,
    setMode, startGame, pauseGame, resumeGame, setDirection, tick, spawnParticles, updateParticles,
    setTimeMode, setCustomTime, setCloudsEnabled, setShadowMode, setFixedShadowAngle, setLampColor,
    setMasterVolume,
    goToMenu,
  } = useGameStore();

  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const particleRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const prevScoreRef = useRef(0);
  const prevStatusRef = useRef(status);
  const prevBugHitRef = useRef(0);
  const [gameTime, setGameTime] = useState({ hour: 12, text: '12:00 PM', icon: '☀️' });
  const [showSettings, setShowSettings] = useState(false);
  const [customHourInput, setCustomHourInput] = useState(String(customTimeHour));
  const [customMinuteInput, setCustomMinuteInput] = useState(String(customTimeMinute));
  const [speedBoostRemaining, setSpeedBoostRemaining] = useState(0);
  const [slowRemaining, setSlowRemaining] = useState(0);
  const [cpuSpeedBoostRemaining, setCpuSpeedBoostRemaining] = useState(0);
  const [cpuSlowRemaining, setCpuSlowRemaining] = useState(0);
  const [immortalRemaining, setImmortalRemaining] = useState(0);
  const [cpuImmortalRemaining, setCpuImmortalRemaining] = useState(0);
  const [powerUpExpiry, setPowerUpExpiry] = useState(0);

  
  useEffect(() => {
    setCustomHourInput(String(customTimeHour));
  }, [customTimeHour]);
  useEffect(() => {
    setCustomMinuteInput(String(customTimeMinute));
  }, [customTimeMinute]);

  
  useEffect(() => {
    if (status === 'playing') {
      if (tickRef.current) clearInterval(tickRef.current);
      tickRef.current = setInterval(() => tick(), speed);
    } else {
      if (tickRef.current) { clearInterval(tickRef.current); tickRef.current = null; }
    }
    return () => { if (tickRef.current) clearInterval(tickRef.current); };
  }, [status, speed, tick]);

  
  useEffect(() => {
    if (status === 'playing') {
      particleRef.current = setInterval(() => updateParticles(1 / 60), 16);
    } else {
      if (particleRef.current) { clearInterval(particleRef.current); particleRef.current = null; }
    }
    return () => { if (particleRef.current) clearInterval(particleRef.current); };
  }, [status, updateParticles]);

  
  useEffect(() => {
    const { setMasterVolume: setAudioVolume } = require('@/game/sounds');
    setAudioVolume(masterVolume / 100);
  }, []); 

  
  useEffect(() => {
    const interval = setInterval(() => {
      const elapsed = performance.now() / 1000;
      const hour = getGameHour(elapsed);
      setGameTime({ hour, text: formatGameTime(hour), icon: getTimeIcon(hour) });
      
      if (speedBoostEnd > 0) {
        const remaining = Math.max(0, Math.ceil((speedBoostEnd - Date.now()) / 1000));
        setSpeedBoostRemaining(remaining);
      } else {
        setSpeedBoostRemaining(0);
      }
      
      if (slowEnd > 0) {
        const remaining = Math.max(0, Math.ceil((slowEnd - Date.now()) / 1000));
        setSlowRemaining(remaining);
      } else {
        setSlowRemaining(0);
      }
      
      if (cpuSpeedBoostEnd > 0) {
        const remaining = Math.max(0, Math.ceil((cpuSpeedBoostEnd - Date.now()) / 1000));
        setCpuSpeedBoostRemaining(remaining);
      } else {
        setCpuSpeedBoostRemaining(0);
      }
      
      if (cpuSlowEnd > 0) {
        const remaining = Math.max(0, Math.ceil((cpuSlowEnd - Date.now()) / 1000));
        setCpuSlowRemaining(remaining);
      } else {
        setCpuSlowRemaining(0);
      }
      
      if (immortalEnd > 0) {
        const remaining = Math.max(0, Math.ceil((immortalEnd - Date.now()) / 1000));
        setImmortalRemaining(remaining);
      } else {
        setImmortalRemaining(0);
      }
      
      if (cpuImmortalEnd > 0) {
        const remaining = Math.max(0, Math.ceil((cpuImmortalEnd - Date.now()) / 1000));
        setCpuImmortalRemaining(remaining);
      } else {
        setCpuImmortalRemaining(0);
      }
      
      if (foodPowerUp !== 'none' && foodSpawnTime > 0) {
        const expiryRemaining = Math.max(0, Math.ceil((POWERUP_EXPIRY - (Date.now() - foodSpawnTime)) / 1000));
        setPowerUpExpiry(expiryRemaining);
      } else {
        setPowerUpExpiry(0);
      }
    }, 100);
    return () => clearInterval(interval);
  }, [speedBoostEnd, slowEnd, cpuSpeedBoostEnd, cpuSlowEnd, immortalEnd, cpuImmortalEnd, foodPowerUp, foodSpawnTime]);

  
  const prevFoodPowerUpRef = useRef<PowerUpType>('none');
  useEffect(() => {
    if (prevScoreRef.current < score && status === 'playing') {
      
      if (prevFoodPowerUpRef.current !== 'none') {
        playPowerUpSound();
      } else {
        playEatSound();
      }
      prevFoodPowerUpRef.current = foodPowerUp;
      const [wx, , wz] = gridToWorld(food.x, food.z, gridSize);
      spawnParticles(wx, wz);
    }
    
    prevFoodPowerUpRef.current = foodPowerUp;
    prevScoreRef.current = score;
  }, [score, status, food, spawnParticles, gridSize, foodPowerUp]);

  
  useEffect(() => {
    if (bugHitTime > 0 && bugHitTime !== prevBugHitRef.current) playBugHitSound();
    prevBugHitRef.current = bugHitTime;
  }, [bugHitTime]);

  
  useEffect(() => {
    if (status === 'gameover' && prevStatusRef.current === 'playing') { playGameOverSound(); stopAmbientSound(); }
    if (status === 'playing' && prevStatusRef.current === 'menu') { playStartSound(); startAmbientSound(); }
    prevStatusRef.current = status;
  }, [status]);

  
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    const keyMap: Record<string, DirectionKey> = {
      ArrowUp: 'UP', ArrowDown: 'DOWN', ArrowLeft: 'LEFT', ArrowRight: 'RIGHT',
      w: 'UP', W: 'UP', s: 'DOWN', S: 'DOWN', a: 'LEFT', A: 'LEFT', d: 'RIGHT', D: 'RIGHT',
    };
    const dir = keyMap[e.key];
    if (dir) { e.preventDefault(); setDirection(dir); if (status === 'playing') playMoveSound(); }
    if (e.key === ' ' || e.key === 'Escape') { e.preventDefault(); if (status === 'playing') pauseGame(); else if (status === 'paused') resumeGame(); }
    if (e.key === 'Enter' && (status === 'menu' || status === 'gameover')) startGame();
  }, [setDirection, status, pauseGame, resumeGame, startGame]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  
  useEffect(() => {
    let touchStartX = 0;
    let touchStartY = 0;
    let touchStartTime = 0;

    const handleTouchStart = (e: TouchEvent) => {
      const touch = e.touches[0];
      touchStartX = touch.clientX;
      touchStartY = touch.clientY;
      touchStartTime = Date.now();
    };

    const handleTouchEnd = (e: TouchEvent) => {
      const touch = e.changedTouches[0];
      const dx = touch.clientX - touchStartX;
      const dy = touch.clientY - touchStartY;
      const dt = Date.now() - touchStartTime;
      const absDx = Math.abs(dx);
      const absDy = Math.abs(dy);
      const minSwipe = 30; 

      
      if (absDx < 15 && absDy < 15 && dt < 300) {
        if (status === 'playing') { pauseGame(); return; }
        return;
      }

      
      if (absDx < minSwipe && absDy < minSwipe) return;

      if (status !== 'playing') return;

      if (absDx > absDy) {
        
        setDirection(dx > 0 ? 'RIGHT' : 'LEFT');
        playMoveSound();
      } else {
        
        setDirection(dy > 0 ? 'DOWN' : 'UP');
        playMoveSound();
      }
    };

    window.addEventListener('touchstart', handleTouchStart, { passive: true });
    window.addEventListener('touchend', handleTouchEnd, { passive: true });
    return () => {
      window.removeEventListener('touchstart', handleTouchStart);
      window.removeEventListener('touchend', handleTouchEnd);
    };
  }, [setDirection, status, pauseGame, resumeGame, startGame]);

  const isArcade = mode === 'arcade';
  const openSideCount = [openSides.top, openSides.bottom, openSides.left, openSides.right].filter(Boolean).length;

  
  const handleCustomHourChange = (val: string) => {
    setCustomHourInput(val);
    const num = parseInt(val, 10);
    if (!isNaN(num) && num >= 0 && num <= 23) {
      setCustomTime(num, customTimeMinute);
    }
  };

  const handleCustomMinuteChange = (val: string) => {
    setCustomMinuteInput(val);
    const num = parseInt(val, 10);
    if (!isNaN(num) && num >= 0 && num <= 59) {
      setCustomTime(customTimeHour, num);
    }
  };

  const handleCustomHourBlur = () => {
    const num = parseInt(customHourInput, 10);
    if (isNaN(num) || num < 0 || num > 23) {
      setCustomHourInput(String(customTimeHour));
    }
  };

  const handleCustomMinuteBlur = () => {
    const num = parseInt(customMinuteInput, 10);
    if (isNaN(num) || num < 0 || num > 59) {
      setCustomMinuteInput(String(customTimeMinute));
    }
  };

  
  const timeModeOptions: { mode: TimeMode; label: string; icon: string }[] = [
    { mode: 'cycle', label: 'Cycle', icon: '🔄' },
    { mode: 'day', label: 'Day', icon: '☀️' },
    { mode: 'night', label: 'Night', icon: '🌙' },
    { mode: 'custom', label: 'Custom', icon: '🕐' },
  ];

  return (
    <div className="absolute inset-0 pointer-events-none" style={{ zIndex: 10 }}>
      
      {(status === 'playing' || status === 'paused') && (
        <>
          
          <div className="absolute top-4 left-4 right-4 flex justify-between items-start pointer-events-none">
            <div className="bg-black/60 backdrop-blur-sm rounded-xl px-4 py-3 border border-white/10">
              <div className="text-emerald-400 text-xs font-semibold uppercase tracking-wider">Score</div>
              <div className="text-white text-3xl font-bold tabular-nums">{score}</div>
            </div>

            
            <div className="absolute left-1/2 -translate-x-1/2 bg-black/60 backdrop-blur-sm rounded-xl px-3 py-2 border border-white/10 flex flex-col items-center gap-0.5">
              <div className={`text-xs font-bold uppercase tracking-wider ${isArcade ? 'text-orange-400' : 'text-blue-400'}`}>
                {isArcade ? 'Arcade' : 'Classic'}
              </div>
              <div className="text-gray-400 text-[10px]">{gridSize}x{gridSize}</div>
              {openSideCount > 0 && <div className="text-cyan-400 text-[10px]">Wrap {openSideCount === 4 ? 'All' : `${openSideCount} side${openSideCount > 1 ? 's' : ''}`}</div>}
              <div className="border-t border-white/10 w-full my-0.5" />
              <div className="text-[11px] tabular-nums">{gameTime.icon} {gameTime.text}</div>
            </div>

            
            <div className="invisible">
              <div className="bg-black/60 backdrop-blur-sm rounded-xl px-4 py-3 border border-white/10">
                <div className="text-emerald-400 text-xs font-semibold uppercase tracking-wider">&nbsp;</div>
                <div className="text-white text-3xl font-bold tabular-nums">&nbsp;</div>
              </div>
            </div>
          </div>

          
          <div className="absolute top-[76px] left-4 flex flex-col gap-2 pointer-events-none">
            
            {status === 'playing' && (
              <div className="bg-black/40 backdrop-blur-sm rounded-lg px-3 py-1.5 border border-white/5">
                <div className="text-gray-400 text-xs">Speed</div>
                <div className="w-20 h-1.5 bg-gray-700 rounded-full mt-1">
                  <div className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-yellow-500 transition-all duration-300"
                    style={{ width: `${Math.min(100, ((200 - speed) / (200 - 80)) * 100)}%` }} />
                </div>
              </div>
            )}
            
            {immortalEnd > 0 && immortalRemaining > 0 && (
              <div className="bg-blue-900/50 backdrop-blur-sm rounded-lg px-3 py-1.5 border border-blue-400/30 animate-pulse">
                <div className="text-blue-300 text-xs font-semibold flex items-center gap-1.5">
                  <span>👻</span> <span>Ghost: {immortalRemaining}s</span>
                </div>
              </div>
            )}
            
            {foodPowerUp !== 'none' && (
              <div className={`backdrop-blur-sm rounded-lg px-3 py-1.5 border ${
                foodPowerUp === 'black' ? 'bg-purple-900/50 border-purple-500/30' :
                foodPowerUp === 'golden' ? 'bg-yellow-900/50 border-yellow-500/30' :
                foodPowerUp === 'immortal' ? 'bg-blue-900/50 border-blue-500/30' :
                foodPowerUp === 'growth' ? 'bg-green-900/50 border-green-500/30' :
                foodPowerUp === 'slow' ? 'bg-gray-700/50 border-gray-400/30' :
                'bg-red-900/50 border-red-500/30'
              }`}>
                <div className={`text-xs font-semibold flex items-center gap-1.5 ${
                  foodPowerUp === 'black' ? 'text-purple-400' :
                  foodPowerUp === 'golden' ? 'text-yellow-400' :
                  foodPowerUp === 'immortal' ? 'text-blue-400' :
                  foodPowerUp === 'growth' ? 'text-green-400' :
                  foodPowerUp === 'slow' ? 'text-gray-300' :
                  'text-red-400'
                }`}>
                  <span>{foodPowerUp === 'golden' ? '💰' : foodPowerUp === 'immortal' ? '👻' : foodPowerUp === 'growth' ? '🌿' : foodPowerUp === 'speed' ? '⚡' : foodPowerUp === 'slow' ? '🐌' : '💀'}</span>
                  <span>{foodPowerUp === 'golden' ? 'Golden Apple' : foodPowerUp === 'immortal' ? 'Immortal Apple' : foodPowerUp === 'growth' ? 'Growth Apple' : foodPowerUp === 'speed' ? 'Speed Apple' : foodPowerUp === 'slow' ? 'Slow Apple' : 'Black Apple'}</span>
                  {powerUpExpiry > 0 && <span className="text-gray-400 ml-1">({powerUpExpiry}s)</span>}
                </div>
              </div>
            )}
          </div>

          
          <div className="absolute top-[76px] right-4 flex flex-col gap-2 pointer-events-none">
            
            {cpuAlive && (
              <div className="bg-black/60 backdrop-blur-sm rounded-xl px-4 py-3 border border-yellow-500/20">
                <div className="text-yellow-400 text-xs font-semibold uppercase tracking-wider">CPU Snake</div>
                <div className="text-yellow-300 text-xl font-bold tabular-nums">{cpuScore}</div>
              </div>
            )}
            
            {status === 'playing' && (
              <div className="bg-black/40 backdrop-blur-sm rounded-lg px-3 py-1.5 border border-white/5">
                <div className="text-gray-400 text-xs">Length</div>
                <div className="text-white text-sm font-semibold">{snake.length}</div>
              </div>
            )}
            
            {speedBoostEnd > 0 && speedBoostRemaining > 0 && (
              <div className="bg-red-900/50 backdrop-blur-sm rounded-lg px-3 py-1.5 border border-red-500/20 animate-pulse">
                <div className="text-red-300 text-xs font-semibold flex items-center gap-1.5">
                  <span>⚡</span> <span>Speed x2: {speedBoostRemaining}s</span>
                </div>
              </div>
            )}
            
            {slowEnd > 0 && slowRemaining > 0 && (
              <div className="bg-gray-700/50 backdrop-blur-sm rounded-lg px-3 py-1.5 border border-gray-400/20 animate-pulse">
                <div className="text-gray-300 text-xs font-semibold flex items-center gap-1.5">
                  <span>🐌</span> <span>Slow x2: {slowRemaining}s</span>
                </div>
              </div>
            )}
            
            {cpuAlive && (cpuImmortalEnd > 0 || cpuSpeedBoostEnd > 0 || cpuSlowEnd > 0) && (
              <div className="bg-yellow-900/30 backdrop-blur-sm rounded-lg px-3 py-1.5 border border-yellow-500/10">
                <div className="text-yellow-500 text-[10px] font-semibold mb-1">CPU Effects:</div>
                {cpuImmortalEnd > 0 && <div className="text-blue-400 text-[10px] flex items-center gap-1">👻 Ghost: {cpuImmortalRemaining}s</div>}
                {cpuSpeedBoostEnd > 0 && <div className="text-red-400 text-[10px] flex items-center gap-1">⚡ Speed x2: {cpuSpeedBoostRemaining}s</div>}
                {cpuSlowEnd > 0 && <div className="text-gray-400 text-[10px] flex items-center gap-1">🐌 Slow x2: {cpuSlowRemaining}s</div>}
              </div>
            )}
          </div>
        </>
      )}

      
      {status === 'menu' && !showSettings && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-auto">
          <div className="bg-black/70 backdrop-blur-md rounded-2xl p-8 max-w-md w-full mx-4 border border-white/10 shadow-2xl">
            <div className="text-center">
              <div className="text-6xl mb-2">🐍</div>
              <h1 className="text-4xl font-bold text-white mb-2">3D Snake</h1>
              <p className="text-gray-400 mb-6">Navigate the garden. Eat apples. Grow longer.</p>

              <div className="flex gap-3 mb-4">
                <button onClick={() => setMode('classic')}
                  className={`flex-1 py-3 px-4 rounded-xl font-bold text-sm transition-all duration-200 border-2 ${mode === 'classic' ? 'bg-emerald-600/30 border-emerald-500 text-emerald-300' : 'bg-white/5 border-white/10 text-gray-400 hover:border-white/20'}`}>
                  🌿 Classic
                  <div className="text-[10px] font-normal mt-0.5 opacity-70">20x20 • Day/night cycle</div>
                </button>
                <button onClick={() => setMode('arcade')}
                  className={`flex-1 py-3 px-4 rounded-xl font-bold text-sm transition-all duration-200 border-2 ${mode === 'arcade' ? 'bg-orange-600/30 border-orange-500 text-orange-300' : 'bg-white/5 border-white/10 text-gray-400 hover:border-white/20'}`}>
                  🎮 Arcade
                  <div className="text-[10px] font-normal mt-0.5 opacity-70">Random maps • Special features</div>
                </button>
              </div>

              {isArcade && (
                <div className="bg-orange-900/20 rounded-lg p-3 mb-4 border border-orange-500/10 text-left">
                  <div className="text-orange-400 text-xs font-semibold mb-1">Arcade features (random per game):</div>
                  <div className="grid grid-cols-2 gap-1 text-[11px] text-gray-400">
                    <div>🧱 Maze walls</div>
                    <div>🔄 Wrap-around edges</div>
                    <div>🐍 CPU snake rival</div>
                    <div>🐛 Apple-pushing bug</div>
                    <div>🏮 Street lamps</div>
                    <div>✨ Night fireflies</div>
                    <div>🍎 Power-ups (6 types!)</div>
                  </div>
                </div>
              )}

              <button onClick={startGame}
                className={`w-full font-bold py-3 px-6 rounded-xl transition-all duration-200 transform hover:scale-105 active:scale-95 shadow-lg mb-4 ${isArcade ? 'bg-orange-600 hover:bg-orange-500 shadow-orange-900/30 text-white' : 'bg-emerald-600 hover:bg-emerald-500 shadow-emerald-900/30 text-white'}`}>
                {isArcade ? 'Generate Map & Play' : 'Start Game'}
              </button>

              <div className="space-y-1 text-sm text-gray-500">
                <p>🎮 Arrow Keys / WASD to move</p>
                <p>📱 Swipe to steer • Tap to pause</p>
                <p>⏸️ Space or Esc to pause</p>
              </div>

              
              <button
                onClick={() => setShowSettings(true)}
                className="mt-4 inline-flex items-center gap-1.5 bg-white/10 hover:bg-white/15 border border-white/10 rounded-lg px-4 py-2 text-xs text-white transition-colors"
              >
                <span>⚙️</span>
                <span>Settings</span>
              </button>

              {highScore > 0 && <div className="mt-4 text-amber-400 font-semibold">🏆 High Score: {highScore}</div>}
            </div>
          </div>
        </div>
      )}

      
      {status === 'menu' && showSettings && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-auto">
          <div className="bg-black/70 backdrop-blur-md rounded-2xl p-6 max-w-md w-full mx-4 border border-white/10 shadow-2xl max-h-[90vh] overflow-y-auto custom-scrollbar">
            
            <div className="flex items-center gap-3 mb-5">
              <button
                onClick={() => setShowSettings(false)}
                className="flex items-center gap-1 text-sm text-gray-400 hover:text-white transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
                Back
              </button>
              <h2 className="text-xl font-bold text-white flex-1">⚙️ Settings</h2>
            </div>

            
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-emerald-400 uppercase tracking-wider mb-3">Graphics Settings</h3>

              
              <div className="bg-white/5 rounded-xl p-4 mb-3 border border-white/5">
                <div className="text-white text-sm font-medium mb-2">🕐 Time Control</div>
                <div className="flex flex-wrap gap-2 mb-2">
                  {timeModeOptions.map(opt => (
                    <button
                      key={opt.mode}
                      onClick={() => setTimeMode(opt.mode)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 border ${
                        timeMode === opt.mode
                          ? 'bg-emerald-600/30 border-emerald-500 text-emerald-300'
                          : 'bg-white/5 border-white/10 text-gray-400 hover:border-white/20 hover:text-white'
                      }`}
                    >
                      {opt.icon} {opt.label}
                    </button>
                  ))}
                </div>
                {timeMode === 'custom' && (
                  <div className="flex items-center gap-2 mt-2 pl-1">
                    <label className="text-gray-400 text-xs">Hours:</label>
                    <input
                      type="number"
                      min={0}
                      max={23}
                      value={customHourInput}
                      onChange={(e) => handleCustomHourChange(e.target.value)}
                      onBlur={handleCustomHourBlur}
                      className="w-14 bg-black/40 border border-white/10 rounded-md px-2 py-1 text-xs text-white text-center focus:outline-none focus:border-emerald-500/50 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                    />
                    <label className="text-gray-400 text-xs">Minutes:</label>
                    <input
                      type="number"
                      min={0}
                      max={59}
                      value={customMinuteInput}
                      onChange={(e) => handleCustomMinuteChange(e.target.value)}
                      onBlur={handleCustomMinuteBlur}
                      className="w-14 bg-black/40 border border-white/10 rounded-md px-2 py-1 text-xs text-white text-center focus:outline-none focus:border-emerald-500/50 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                    />
                  </div>
                )}
              </div>

              
              <div className="bg-white/5 rounded-xl p-4 mb-3 border border-white/5">
                <div className="flex items-center justify-between">
                  <div className="text-white text-sm font-medium">☁️ Clouds</div>
                  <button
                    onClick={() => setCloudsEnabled(!cloudsEnabled)}
                    className={`relative w-10 h-5 rounded-full transition-colors duration-200 ${
                      cloudsEnabled ? 'bg-emerald-500' : 'bg-gray-600'
                    }`}
                    aria-label={cloudsEnabled ? 'Disable clouds' : 'Enable clouds'}
                  >
                    <span
                      className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-transform duration-200 ${
                        cloudsEnabled ? 'translate-x-5' : 'translate-x-0'
                      }`}
                    />
                  </button>
                </div>
              </div>

              
              <div className="bg-white/5 rounded-xl p-4 mb-3 border border-white/5">
                <div className="text-white text-sm font-medium mb-2">🌑 Shadow</div>
                <div className="flex gap-2 mb-2">
                  <button
                    onClick={() => setShadowMode('dynamic')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 border ${
                      shadowMode === 'dynamic'
                        ? 'bg-emerald-600/30 border-emerald-500 text-emerald-300'
                        : 'bg-white/5 border-white/10 text-gray-400 hover:border-white/20 hover:text-white'
                    }`}
                  >
                    Dynamic
                  </button>
                  <button
                    onClick={() => setShadowMode('fixed')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 border ${
                      shadowMode === 'fixed'
                        ? 'bg-emerald-600/30 border-emerald-500 text-emerald-300'
                        : 'bg-white/5 border-white/10 text-gray-400 hover:border-white/20 hover:text-white'
                    }`}
                  >
                    Fixed
                  </button>
                </div>
                {shadowMode === 'fixed' && (
                  <div className="mt-3">
                    <div className="flex items-center gap-3">
                      <div className="flex-1">
                        <input
                          type="range"
                          min={0}
                          max={360}
                          value={fixedShadowAngle}
                          onChange={(e) => setFixedShadowAngle(parseInt(e.target.value, 10))}
                          className="w-full h-1.5 bg-gray-700 rounded-full appearance-none cursor-pointer accent-emerald-500"
                        />
                        <div className="flex justify-between text-[9px] text-gray-500 mt-0.5">
                          <span>0°</span>
                          <span>90°</span>
                          <span>180°</span>
                          <span>270°</span>
                          <span>360°</span>
                        </div>
                      </div>
                      <TreeShadowDemo angle={fixedShadowAngle} />
                    </div>
                  </div>
                )}
              </div>

              
              <div className="bg-white/5 rounded-xl p-4 border border-white/5">
                <div className="text-white text-sm font-medium mb-2">🏮 Lamp Color</div>
                <div className="flex gap-2 mb-2">
                  <button
                    onClick={() => setLampColor('yellow')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 border ${
                      lampColor === 'yellow'
                        ? 'bg-amber-600/30 border-amber-500 text-amber-300'
                        : 'bg-white/5 border-white/10 text-gray-400 hover:border-white/20 hover:text-white'
                    }`}
                  >
                    🟡 Yellow
                  </button>
                  <button
                    onClick={() => setLampColor('white')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 border ${
                      lampColor === 'white'
                        ? 'bg-blue-600/30 border-blue-400 text-blue-200'
                        : 'bg-white/5 border-white/10 text-gray-400 hover:border-white/20 hover:text-white'
                    }`}
                  >
                    ⚪ White
                  </button>
                </div>
                <div className="flex justify-center mt-2">
                  <LampPreview color={lampColor} />
                </div>
              </div>
            </div>

            
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-emerald-400 uppercase tracking-wider mb-3">Audio Settings</h3>

              <div className="bg-white/5 rounded-xl p-4 border border-white/5">
                <div className="text-white text-sm font-medium mb-2">🔊 Volume</div>
                <div className="flex items-center gap-3">
                  <span className="text-gray-400 text-xs w-6 text-right">{masterVolume}%</span>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={masterVolume}
                    onChange={(e) => setMasterVolume(parseInt(e.target.value, 10))}
                    className="flex-1 h-1.5 bg-gray-700 rounded-full appearance-none cursor-pointer accent-emerald-500"
                  />
                  <span className="text-gray-500 text-xs w-6">
                    {masterVolume === 0 ? '🔇' : masterVolume < 50 ? '🔉' : '🔊'}
                  </span>
                </div>
              </div>
            </div>

            
            <button
              onClick={() => setShowSettings(false)}
              className="w-full bg-white/10 hover:bg-white/15 text-white font-medium py-2.5 px-4 rounded-xl transition-all duration-200 text-sm border border-white/10"
            >
              ← Back to Menu
            </button>
          </div>
        </div>
      )}

      
      {status === 'paused' && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/30 pointer-events-auto">
          <div className="bg-black/70 backdrop-blur-md rounded-2xl p-8 max-w-sm w-full mx-4 border border-white/10">
            <div className="text-center">
              <div className="text-4xl mb-2">⏸️</div>
              <h2 className="text-2xl font-bold text-white mb-4">Paused</h2>
              <button onClick={resumeGame} className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 px-6 rounded-xl transition-all duration-200 transform hover:scale-105 active:scale-95">Resume</button>
            </div>
          </div>
        </div>
      )}

      
      {status === 'gameover' && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-auto">
          <div className="bg-black/70 backdrop-blur-md rounded-2xl p-8 max-w-md w-full mx-4 border border-red-500/20 shadow-2xl">
            <div className="text-center">
              {gameResult === 'won' ? (<><div className="text-4xl mb-2">🏆</div><h2 className="text-3xl font-bold text-amber-400 mb-2">You Won!</h2><p className="text-gray-400 mb-4">You beat the CPU snake!</p></>)
              : gameResult === 'lost' ? (<><div className="text-4xl mb-2">💀</div><h2 className="text-3xl font-bold text-red-400 mb-2">Game Over</h2><p className="text-gray-400 mb-4">CPU snake beat you!</p></>)
              : gameResult === 'tied' ? (<><div className="text-4xl mb-2">🤝</div><h2 className="text-3xl font-bold text-gray-300 mb-2">Tied!</h2><p className="text-gray-400 mb-4">Same score as CPU!</p></>)
              : (<><div className="text-4xl mb-2">💀</div><h2 className="text-3xl font-bold text-red-400 mb-2">Game Over</h2><p className="text-gray-400 mb-4">You crashed!</p></>)}

              <div className={`grid ${cpuAlive || gameResult ? 'grid-cols-3' : 'grid-cols-2'} gap-3 mb-6`}>
                <div className="bg-white/5 rounded-xl p-3"><div className="text-gray-400 text-xs uppercase">Score</div><div className="text-white text-2xl font-bold">{score}</div></div>
                {(cpuAlive || gameResult) && <div className="bg-yellow-900/20 rounded-xl p-3"><div className="text-yellow-400 text-xs uppercase">CPU</div><div className="text-yellow-300 text-2xl font-bold">{cpuScore}</div></div>}
                <div className="bg-white/5 rounded-xl p-3"><div className="text-amber-400 text-xs uppercase">Best</div><div className="text-amber-400 text-2xl font-bold">{highScore}</div></div>
              </div>

              {score >= highScore && score > 0 && <div className="text-yellow-400 font-bold mb-4 animate-bounce">🎉 New High Score! 🎉</div>}

              {isArcade && mapConfig && (
                <div className="bg-white/5 rounded-lg p-2 mb-4 text-xs text-gray-500">
                  {gridSize}x{gridSize} map
                  {mapConfig.walls.length > 0 && ` • ${mapConfig.walls.length} walls`}
                  {openSideCount > 0 && ` • Wrap ${openSideCount === 4 ? 'all' : `${openSideCount} side${openSideCount > 1 ? 's' : ''}`}`}
                  {mapConfig.hasCpuSnake && ' • CPU snake'}
                  {mapConfig.hasBug && ' • Bug'}
                  {mapConfig.hasLamps && ' • Lamps'}
                  {mapConfig.hasFireflies && ' • Fireflies'}
                </div>
              )}

              <button onClick={startGame}
                className={`w-full font-bold py-3 px-6 rounded-xl transition-all duration-200 transform hover:scale-105 active:scale-95 shadow-lg mb-3 ${isArcade ? 'bg-orange-600 hover:bg-orange-500 text-white' : 'bg-emerald-600 hover:bg-emerald-500 text-white'}`}>
                {isArcade ? 'New Random Map' : 'Play Again'}
              </button>
              <button onClick={goToMenu}
                className="w-full bg-white/10 hover:bg-white/15 text-white font-medium py-2.5 px-4 rounded-xl transition-all duration-200 text-sm border border-white/10">
                ← Return to Main Menu
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
