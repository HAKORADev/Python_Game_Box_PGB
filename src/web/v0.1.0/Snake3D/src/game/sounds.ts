let audioCtx: AudioContext | null = null;
let masterGain: GainNode | null = null;

function getAudioCtx(): AudioContext {
  if (!audioCtx) {
    audioCtx = new AudioContext();
    masterGain = audioCtx.createGain();
    masterGain.connect(audioCtx.destination);
  }
  if (audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
  return audioCtx;
}

function getMasterGain(): GainNode {
  getAudioCtx();
  return masterGain!;
}

function getDestination(): AudioNode {
  return getMasterGain();
}

export function setMasterVolume(value: number) {
  const gain = getMasterGain();
  gain.gain.setValueAtTime(Math.max(0, Math.min(1, value)), getAudioCtx().currentTime);
}

export function playEatSound() {
  try {
    const ctx = getAudioCtx();
    const now = ctx.currentTime;
    const dest = getDestination();

    
    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(600, now);
    osc1.frequency.exponentialRampToValueAtTime(1200, now + 0.05);
    osc1.frequency.exponentialRampToValueAtTime(300, now + 0.15);
    gain1.gain.setValueAtTime(0.3, now);
    gain1.gain.exponentialRampToValueAtTime(0.01, now + 0.15);
    osc1.connect(gain1).connect(dest);
    osc1.start(now);
    osc1.stop(now + 0.15);

    
    const osc2 = ctx.createOscillator();
    const gain2 = ctx.createGain();
    osc2.type = 'sine';
    osc2.frequency.setValueAtTime(880, now + 0.02);
    osc2.frequency.exponentialRampToValueAtTime(440, now + 0.1);
    gain2.gain.setValueAtTime(0.2, now + 0.02);
    gain2.gain.exponentialRampToValueAtTime(0.01, now + 0.12);
    osc2.connect(gain2).connect(dest);
    osc2.start(now + 0.02);
    osc2.stop(now + 0.12);

    
    const osc3 = ctx.createOscillator();
    const gain3 = ctx.createGain();
    osc3.type = 'triangle';
    osc3.frequency.setValueAtTime(1400, now + 0.05);
    osc3.frequency.exponentialRampToValueAtTime(2000, now + 0.2);
    gain3.gain.setValueAtTime(0.1, now + 0.05);
    gain3.gain.exponentialRampToValueAtTime(0.01, now + 0.25);
    osc3.connect(gain3).connect(dest);
    osc3.start(now + 0.05);
    osc3.stop(now + 0.25);
  } catch (e) {
    
  }
}

export function playPowerUpSound() {
  try {
    const ctx = getAudioCtx();
    const now = ctx.currentTime;
    const dest = getDestination();

    
    const notes = [880, 1108.73, 1318.51, 1760, 2217.46]; 
    notes.forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      const startTime = now + i * 0.06;
      osc.frequency.setValueAtTime(freq, startTime);
      gain.gain.setValueAtTime(0, startTime);
      gain.gain.linearRampToValueAtTime(0.15, startTime + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.01, startTime + 0.2);
      osc.connect(gain).connect(dest);
      osc.start(startTime);
      osc.stop(startTime + 0.2);
    });

    
    const shimmer = ctx.createOscillator();
    const shimmerGain = ctx.createGain();
    shimmer.type = 'triangle';
    shimmer.frequency.setValueAtTime(2637.02, now + 0.2); 
    shimmer.frequency.exponentialRampToValueAtTime(3520, now + 0.35); 
    shimmerGain.gain.setValueAtTime(0, now + 0.2);
    shimmerGain.gain.linearRampToValueAtTime(0.08, now + 0.22);
    shimmerGain.gain.exponentialRampToValueAtTime(0.01, now + 0.45);
    shimmer.connect(shimmerGain).connect(dest);
    shimmer.start(now + 0.2);
    shimmer.stop(now + 0.45);

    
    const sparkle = ctx.createOscillator();
    const sparkleGain = ctx.createGain();
    sparkle.type = 'sine';
    sparkle.frequency.setValueAtTime(3000, now + 0.15);
    sparkle.frequency.exponentialRampToValueAtTime(4000, now + 0.25);
    sparkleGain.gain.setValueAtTime(0, now + 0.15);
    sparkleGain.gain.linearRampToValueAtTime(0.06, now + 0.17);
    sparkleGain.gain.exponentialRampToValueAtTime(0.01, now + 0.35);
    sparkle.connect(sparkleGain).connect(dest);
    sparkle.start(now + 0.15);
    sparkle.stop(now + 0.35);
  } catch (e) {
    
  }
}

export function playGameOverSound() {
  try {
    const ctx = getAudioCtx();
    const now = ctx.currentTime;
    const dest = getDestination();

    
    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = 'sawtooth';
    osc1.frequency.setValueAtTime(150, now);
    osc1.frequency.exponentialRampToValueAtTime(50, now + 0.5);
    gain1.gain.setValueAtTime(0.25, now);
    gain1.gain.exponentialRampToValueAtTime(0.01, now + 0.5);
    osc1.connect(gain1).connect(dest);
    osc1.start(now);
    osc1.stop(now + 0.5);

    
    const osc2 = ctx.createOscillator();
    const gain2 = ctx.createGain();
    osc2.type = 'square';
    osc2.frequency.setValueAtTime(440, now + 0.1);
    osc2.frequency.exponentialRampToValueAtTime(110, now + 0.6);
    gain2.gain.setValueAtTime(0.15, now + 0.1);
    gain2.gain.exponentialRampToValueAtTime(0.01, now + 0.6);
    osc2.connect(gain2).connect(dest);
    osc2.start(now + 0.1);
    osc2.stop(now + 0.6);

    
    const bufferSize = ctx.sampleRate * 0.15;
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = (Math.random() * 2 - 1) * Math.exp(-i / (ctx.sampleRate * 0.03));
    }
    const noise = ctx.createBufferSource();
    noise.buffer = buffer;
    const noiseGain = ctx.createGain();
    noiseGain.gain.setValueAtTime(0.2, now);
    noiseGain.gain.exponentialRampToValueAtTime(0.01, now + 0.15);
    noise.connect(noiseGain).connect(dest);
    noise.start(now);
  } catch (e) {
    
  }
}

export function playMoveSound() {
  try {
    const ctx = getAudioCtx();
    const now = ctx.currentTime;
    const dest = getDestination();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(200, now);
    gain.gain.setValueAtTime(0.03, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.05);
    osc.connect(gain).connect(dest);
    osc.start(now);
    osc.stop(now + 0.05);
  } catch (e) {
    
  }
}

export function playStartSound() {
  try {
    const ctx = getAudioCtx();
    const now = ctx.currentTime;
    const dest = getDestination();

    const notes = [523.25, 659.25, 783.99, 1046.5]; 
    notes.forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, now + i * 0.1);
      gain.gain.setValueAtTime(0, now + i * 0.1);
      gain.gain.linearRampToValueAtTime(0.15, now + i * 0.1 + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.01, now + i * 0.1 + 0.15);
      osc.connect(gain).connect(dest);
      osc.start(now + i * 0.1);
      osc.stop(now + i * 0.1 + 0.15);
    });
  } catch (e) {
    
  }
}

export function playBugHitSound() {
  try {
    const ctx = getAudioCtx();
    const now = ctx.currentTime;
    const dest = getDestination();

    
    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = 'sawtooth';
    osc1.frequency.setValueAtTime(200, now);
    osc1.frequency.exponentialRampToValueAtTime(80, now + 0.3);
    gain1.gain.setValueAtTime(0.18, now);
    gain1.gain.exponentialRampToValueAtTime(0.01, now + 0.3);
    osc1.connect(gain1).connect(dest);
    osc1.start(now);
    osc1.stop(now + 0.3);

    
    const bufferSize = Math.floor(ctx.sampleRate * 0.1);
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = (Math.random() * 2 - 1) * Math.exp(-i / (ctx.sampleRate * 0.02));
    }
    const noise = ctx.createBufferSource();
    noise.buffer = buffer;
    const noiseGain = ctx.createGain();
    noiseGain.gain.setValueAtTime(0.15, now);
    noiseGain.gain.exponentialRampToValueAtTime(0.01, now + 0.1);
    noise.connect(noiseGain).connect(dest);
    noise.start(now);
  } catch (e) {
    
  }
}

let ambientNode: { source: AudioBufferSourceNode; gain: GainNode } | null = null;

export function startAmbientSound() {
  try {
    const ctx = getAudioCtx();
    const dest = getDestination();
    if (ambientNode) return;

    
    const bufferSize = ctx.sampleRate * 4;
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = Math.random() * 2 - 1;
    }

    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.loop = true;

    
    const filter = ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.setValueAtTime(200, ctx.currentTime);
    filter.Q.setValueAtTime(1, ctx.currentTime);

    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.02, ctx.currentTime);

    source.connect(filter).connect(gain).connect(dest);
    source.start();

    ambientNode = { source, gain };
  } catch (e) {
    
  }
}

export function stopAmbientSound() {
  try {
    if (ambientNode) {
      ambientNode.gain.gain.exponentialRampToValueAtTime(0.001, getAudioCtx().currentTime + 0.5);
      setTimeout(() => {
        try {
          ambientNode?.source.stop();
        } catch {  }
        ambientNode = null;
      }, 600);
    }
  } catch (e) {
    ambientNode = null;
  }
}
