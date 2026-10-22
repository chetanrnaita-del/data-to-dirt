/**
 * ==============================================================================
 * DATA-TO-DIRT — Procedural Web Audio API Chiptune Synthesizer
 * Zero external audio files; 100% procedural retro waveforms (Square, Triangle, Noise)
 * ==============================================================================
 */

class RetroAudioSynth {
  constructor() {
    this.ctx = null;
    this.masterGain = null;
    this.volume = 0.3;
    this.muted = false;
    this.initialized = false;
  }

  init() {
    if (this.initialized) return;
    try {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextClass) return;
      this.ctx = new AudioContextClass();
      this.masterGain = this.ctx.createGain();
      this.masterGain.gain.setValueAtTime(this.muted ? 0 : this.volume, this.ctx.currentTime);
      this.masterGain.connect(this.ctx.destination);
      this.initialized = true;
    } catch (e) {
      console.warn("Web Audio API not supported or blocked:", e);
    }
  }

  ensureContext() {
    if (!this.initialized) this.init();
    if (this.ctx && this.ctx.state === "suspended") {
      this.ctx.resume();
    }
  }

  setVolume(vol) {
    this.volume = Math.max(0, Math.min(1, vol));
    if (this.masterGain && !this.muted) {
      this.masterGain.gain.setValueAtTime(this.volume, this.ctx.currentTime);
    }
  }

  toggleMute() {
    this.muted = !this.muted;
    if (this.masterGain) {
      this.masterGain.gain.setValueAtTime(this.muted ? 0 : this.volume, this.ctx.currentTime);
    }
    return this.muted;
  }

  isMuted() {
    return this.muted;
  }

  /** UI Blip: Square wave pitch glide for menu clicks and hovers */
  playBlip() {
    if (this.muted) return;
    this.ensureContext();
    if (!this.ctx) return;

    const t = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = "square";
    osc.frequency.setValueAtTime(440, t);
    osc.frequency.exponentialRampToValueAtTime(880, t + 0.04);

    gain.gain.setValueAtTime(0.25, t);
    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.05);

    osc.connect(gain);
    gain.connect(this.masterGain);

    osc.start(t);
    osc.stop(t + 0.05);
  }

  /** Coin Ding: Two-tone square arpeggio for score & carbon increments */
  playCoinDing() {
    if (this.muted) return;
    this.ensureContext();
    if (!this.ctx) return;

    const t = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = "square";
    osc.frequency.setValueAtTime(987.77, t); // B5
    osc.frequency.setValueAtTime(1318.51, t + 0.06); // E6

    gain.gain.setValueAtTime(0.3, t);
    gain.gain.setValueAtTime(0.3, t + 0.06);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.28);

    osc.connect(gain);
    gain.connect(this.masterGain);

    osc.start(t);
    osc.stop(t + 0.28);
  }

  /** Deletion Poof: Filtered noise sweep for satisfying crunchy file deletion */
  playDeletionPoof() {
    if (this.muted) return;
    this.ensureContext();
    if (!this.ctx) return;

    const t = this.ctx.currentTime;
    const bufferSize = Math.floor(this.ctx.sampleRate * 0.25);
    const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
    const data = buffer.getChannelData(0);

    for (let i = 0; i < bufferSize; i++) {
      data[i] = (Math.random() * 2 - 1) * Math.exp(-i / (bufferSize * 0.4));
    }

    const noise = this.ctx.createBufferSource();
    noise.buffer = buffer;

    const filter = this.ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.setValueAtTime(1200, t);
    filter.frequency.exponentialRampToValueAtTime(60, t + 0.22);

    const gain = this.ctx.createGain();
    gain.gain.setValueAtTime(0.45, t);
    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.24);

    noise.connect(filter);
    filter.connect(gain);
    gain.connect(this.masterGain);

    noise.start(t);
    noise.stop(t + 0.25);
  }

  /** Victory Fanfare: 4-note triangle chord for milestone & tree level up */
  playVictoryFanfare() {
    if (this.muted) return;
    this.ensureContext();
    if (!this.ctx) return;

    const t = this.ctx.currentTime;
    // C5, E5, G5, C6 arpeggio notes
    const notes = [
      { freq: 523.25, time: 0.0, dur: 0.12 },
      { freq: 659.25, time: 0.12, dur: 0.12 },
      { freq: 783.99, time: 0.24, dur: 0.12 },
      { freq: 1046.5, time: 0.36, dur: 0.55 },
    ];

    notes.forEach((n) => {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = "triangle";
      osc.frequency.setValueAtTime(n.freq, t + n.time);

      gain.gain.setValueAtTime(0.35, t + n.time);
      gain.gain.exponentialRampToValueAtTime(0.001, t + n.time + n.dur);

      osc.connect(gain);
      gain.connect(this.masterGain);

      osc.start(t + n.time);
      osc.stop(t + n.time + n.dur);
    });
  }

  /** Gaming Buzzer: Low harsh modulated sawtooth for detected gaming attempts */
  playGamingBuzzer() {
    if (this.muted) return;
    this.ensureContext();
    if (!this.ctx) return;

    const t = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(130.81, t); // C3 harsh bass

    // 20 Hz tremolo effect
    const lfo = this.ctx.createOscillator();
    const lfoGain = this.ctx.createGain();
    lfo.frequency.setValueAtTime(22, t);
    lfoGain.gain.setValueAtTime(0.18, t);
    lfo.connect(lfoGain.gain);

    gain.gain.setValueAtTime(0.4, t);
    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.38);

    osc.connect(gain);
    gain.connect(this.masterGain);

    osc.start(t);
    lfo.start(t);
    osc.stop(t + 0.4);
    lfo.stop(t + 0.4);
  }
}

// Global Audio Singleton
window.RetroAudio = new RetroAudioSynth();
