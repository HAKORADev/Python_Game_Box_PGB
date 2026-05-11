'use client';

import React, { Suspense } from 'react';
import dynamic from 'next/dynamic';

const SnakeScene = dynamic(() => import('@/components/game/SnakeScene'), { ssr: false });
const GameUI = dynamic(() => import('@/components/game/GameUI'), { ssr: false });

function LoadingScreen() {
  return (
    <div className="w-full h-screen flex items-center justify-center bg-gradient-to-b from-sky-900 to-emerald-900">
      <div className="text-center">
        <div className="text-6xl mb-4 animate-bounce">🐍</div>
        <div className="text-white text-2xl font-bold mb-2">3D Snake</div>
        <div className="text-gray-300 text-sm mb-4">Loading...</div>
        <div className="mt-4 w-64 h-2 bg-white/10 rounded-full mx-auto overflow-hidden">
          <div className="h-full bg-gradient-to-r from-cyan-500 via-blue-500 to-purple-500 rounded-full animate-pulse" style={{ width: '80%' }} />
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <div className="w-full h-screen relative overflow-hidden bg-black">
      <Suspense fallback={<LoadingScreen />}>
        <SnakeScene />
        <GameUI />
      </Suspense>
    </div>
  );
}
