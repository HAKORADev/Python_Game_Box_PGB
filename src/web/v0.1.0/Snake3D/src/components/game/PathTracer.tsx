'use client';

import React, { useMemo } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { EffectComposer as R3FEffectComposer, ToneMapping } from '@react-three/postprocessing';
import { Effect, EffectAttribute, BlendFunction, ToneMappingMode } from 'postprocessing';
import * as THREE from 'three';
import { useGameStore } from '@/game/store';
import { getGameHour, getDaylight, getSunPosition, getMoonPosition } from '@/game/constants';

class VolumetricLightEffect extends Effect {
  constructor() {
    super('VolumetricLight', `
      precision highp float;

      uniform sampler2D uDepthBuffer;
      uniform vec3 uSunDir;
      uniform vec3 uSunColor;
      uniform float uSunIntensity;
      uniform vec3 uMoonDir;
      uniform vec3 uMoonColor;
      uniform float uMoonIntensity;
      uniform mat4 uProjectionMatrix;
      uniform mat4 uInverseProjectionMatrix;
      uniform mat4 uViewMatrix;
      uniform mat4 uInverseViewMatrix;
      uniform vec2 uResolution;
      uniform float uDaylight;
      uniform float uTime;

      #ifndef PI
      #define PI 3.14159265359
      #endif

      vec3 reconstructWorldPos(vec2 uv, float depth) {
        vec4 ndc = vec4(uv * 2.0 - 1.0, depth * 2.0 - 1.0, 1.0);
        vec4 viewPos = uInverseProjectionMatrix * ndc;
        viewPos /= viewPos.w;
        return (uInverseViewMatrix * viewPos).xyz;
      }

      float henyeyGreenstein(float cosAngle, float g) {
        float g2 = g * g;
        return (1.0 - g2) / (4.0 * PI * pow(1.0 + g2 - 2.0 * g * cosAngle, 1.5));
      }

      vec3 marchGodRays(vec3 cameraPos, vec3 worldPos, vec2 uv) {
        if (uSunIntensity < 0.01 && uMoonIntensity < 0.01) return vec3(0.0);

        vec3 viewDir = normalize(worldPos - cameraPos);
        float dist = length(worldPos - cameraPos);

        vec3 sunScatter = vec3(0.0);
        if (uSunIntensity > 0.01) {
          float cosAngle = dot(viewDir, uSunDir);
          float phase = henyeyGreenstein(cosAngle, 0.7);

          const int SUN_STEPS = 24;
          for (int i = 0; i < SUN_STEPS; i++) {
            float t = float(i) / float(SUN_STEPS) * dist;
            vec3 pos = cameraPos + viewDir * t;
            float heightFalloff = exp(-max(0.0, pos.y) * 0.04);
            float turb = 1.0 + 0.15 * sin(pos.x * 0.3 + uTime * 0.1) * sin(pos.z * 0.25 + uTime * 0.08);
            float fogDensity = heightFalloff * 0.04 * turb;
            sunScatter += fogDensity * uSunColor * uSunIntensity * phase / float(SUN_STEPS);
          }
          sunScatter *= 1.2;
        }

        vec3 moonScatter = vec3(0.0);
        if (uMoonIntensity > 0.01) {
          float cosAngle = dot(viewDir, uMoonDir);
          float phase = henyeyGreenstein(cosAngle, 0.4);

          const int MOON_STEPS = 16;
          for (int i = 0; i < MOON_STEPS; i++) {
            float t = float(i) / float(MOON_STEPS) * dist;
            vec3 pos = cameraPos + viewDir * t;
            float heightFalloff = exp(-max(0.0, pos.y) * 0.04);
            float fogDensity = heightFalloff * 0.025;
            moonScatter += fogDensity * uMoonColor * uMoonIntensity * phase / float(MOON_STEPS);
          }
          moonScatter *= 1.2; // Stronger moon ray visibility
        }

        return sunScatter + moonScatter;
      }

      void mainImage(const in vec4 inputColor, const in vec2 uv, out vec4 outputColor) {
        float depth = texture2D(uDepthBuffer, uv).x;
        if (depth >= 1.0) { outputColor = inputColor; return; }

        vec3 worldPos = reconstructWorldPos(uv, depth);
        if (worldPos.y < -0.5) { outputColor = inputColor; return; }

        vec3 result = inputColor.rgb;

        vec3 cameraWorldPos = (uInverseViewMatrix * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
        vec3 godRays = marchGodRays(cameraWorldPos, worldPos, uv);
        result += godRays;

        outputColor = vec4(result, 1.0);
      }
    `, {
      attributes: EffectAttribute.DEPTH,
      blendFunction: BlendFunction.NORMAL,
      uniforms: new Map<string, THREE.Uniform>([
        ['uDepthBuffer', new THREE.Uniform(null)],
        ['uSunDir', new THREE.Uniform(new THREE.Vector3(0, 1, 0))],
        ['uSunColor', new THREE.Uniform(new THREE.Color(1, 0.95, 0.8))],
        ['uSunIntensity', new THREE.Uniform(1.5)],
        ['uMoonDir', new THREE.Uniform(new THREE.Vector3(0, 1, 0))],
        ['uMoonColor', new THREE.Uniform(new THREE.Color(0.78, 0.85, 0.94))], 
        ['uMoonIntensity', new THREE.Uniform(0.0)],
        ['uProjectionMatrix', new THREE.Uniform(new THREE.Matrix4())],
        ['uInverseProjectionMatrix', new THREE.Uniform(new THREE.Matrix4())],
        ['uViewMatrix', new THREE.Uniform(new THREE.Matrix4())],
        ['uInverseViewMatrix', new THREE.Uniform(new THREE.Matrix4())],
        ['uResolution', new THREE.Uniform(new THREE.Vector2(1, 1))],
        ['uDaylight', new THREE.Uniform(1)],
        ['uTime', new THREE.Uniform(0)],
      ])
    });
  }
}

export default function PathTracer() {
  const { camera, size } = useThree();
  const gridSize = useGameStore(s => s.gridSize);
  const effect = useMemo(() => new VolumetricLightEffect(), []);

  useFrame((state) => {
    const elapsed = state.clock.elapsedTime;
    const hour = getGameHour(elapsed);
    const daylight = getDaylight(hour);

    const sunPos = getSunPosition(hour, gridSize);
    const sunDir = new THREE.Vector3(sunPos.x, sunPos.y, sunPos.z).normalize();
    const sunElevation = Math.max(0, Math.sin(((hour - 6) / 12) * Math.PI));
    const moonPos = getMoonPosition(hour, gridSize);
    const moonDir = new THREE.Vector3(moonPos.x, moonPos.y, moonPos.z).normalize();
    const moonElevation = Math.max(0, Math.sin((((hour - 18) + 24) % 24 / 12) * Math.PI));
    const moonFactor = Math.max(0, Math.pow(Math.max(0, Math.sin((((hour - 18) + 24) % 24 / 12) * Math.PI)), 0.5));

    const pu = effect.uniforms;
    pu.get('uSunDir')!.value.copy(sunDir);
    pu.get('uSunColor')!.value.setRGB(1.0, 0.95, 0.8);
    pu.get('uSunIntensity')!.value = sunElevation * 2.0;
    pu.get('uMoonDir')!.value.copy(moonDir);
    pu.get('uMoonColor')!.value.setRGB(0.78, 0.85, 0.94); 
    pu.get('uMoonIntensity')!.value = moonFactor * 1.5; 
    pu.get('uProjectionMatrix')!.value.copy(camera.projectionMatrix);
    pu.get('uInverseProjectionMatrix')!.value.copy(camera.projectionMatrix).invert();
    pu.get('uViewMatrix')!.value.copy(camera.matrixWorldInverse);
    pu.get('uInverseViewMatrix')!.value.copy(camera.matrixWorld);
    pu.get('uResolution')!.value.set(size.width, size.height);
    pu.get('uDaylight')!.value = daylight;
    pu.get('uTime')!.value = elapsed;
  });

  return (
    <R3FEffectComposer multisampling={4}>
      
      <primitive object={effect} />
      
      <ToneMapping mode={ToneMappingMode.ACES_FILMIC} />
    </R3FEffectComposer>
  );
}
