/**
 * ==============================================================================
 * DATA-TO-DIRT — 60 FPS Canvas2D Retro Particle System
 * Binary shards, eco-sparkles, celebration confetti, floating text
 * ==============================================================================
 */

class RetroParticleEngine {
  constructor(canvasId = "particle-canvas") {
    this.canvasId = canvasId;
    this.canvas = null;
    this.ctx = null;
    this.particles = [];
    this.texts = [];
    this.lastTime = performance.now();
    this.isRunning = false;

    window.addEventListener("resize", () => this.resize());
  }

  init() {
    this.canvas = document.getElementById(this.canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext("2d");
    this.resize();
    this.start();
  }

  resize() {
    if (!this.canvas) return;
    this.canvas.width = window.innerWidth;
    this.canvas.height = window.innerHeight;
  }

  start() {
    if (this.isRunning) return;
    this.isRunning = true;
    this.lastTime = performance.now();
    requestAnimationFrame((t) => this.loop(t));
  }

  loop(currentTime) {
    if (!this.isRunning) return;
    const dt = Math.min((currentTime - this.lastTime) / 1000.0, 0.1);
    this.lastTime = currentTime;

    this.update(dt);
    this.render();

    requestAnimationFrame((t) => this.loop(t));
  }

  update(dt) {
    // Update particles
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      p.life -= dt;
      if (p.life <= 0) {
        this.particles.splice(i, 1);
        continue;
      }

      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.vy += p.gravity * dt;
      p.vx *= p.drag;

      if (p.hasFlutter) {
        p.flutterPhase += dt * 6;
        p.x += Math.sin(p.flutterPhase) * 0.8;
      }
    }

    // Update floating texts
    for (let i = this.texts.length - 1; i >= 0; i--) {
      const t = this.texts[i];
      t.life -= dt;
      if (t.life <= 0) {
        this.texts.splice(i, 1);
        continue;
      }
      t.y += t.vy * dt;
      t.scale = Math.min(1.2, t.scale + dt * 0.5);
    }
  }

  render() {
    if (!this.ctx) return;
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    // Render particles with pixel art style
    for (const p of this.particles) {
      this.ctx.save();
      const alpha = Math.max(0, p.life / p.maxLife);
      this.ctx.globalAlpha = alpha;
      this.ctx.fillStyle = p.color;

      if (p.type === "glyph") {
        this.ctx.font = `${p.size}px "Courier New", monospace`;
        this.ctx.fillText(p.glyph, Math.round(p.x), Math.round(p.y));
      } else if (p.type === "pixel") {
        this.ctx.fillRect(Math.round(p.x), Math.round(p.y), p.size, p.size);
      } else if (p.type === "sparkle") {
        const sz = p.size;
        const x = Math.round(p.x);
        const y = Math.round(p.y);
        // Retro 4-point star cross
        this.ctx.fillRect(x - sz, y, sz * 2, 2);
        this.ctx.fillRect(x, y - sz, 2, sz * 2);
      }

      this.ctx.restore();
    }

    // Render floating texts
    for (const t of this.texts) {
      this.ctx.save();
      const alpha = Math.max(0, t.life / t.maxLife);
      this.ctx.globalAlpha = alpha;
      this.ctx.fillStyle = t.color;
      this.ctx.font = `bold ${Math.round(14 * t.scale)}px "Courier New", monospace`;
      this.ctx.shadowColor = "#000000";
      this.ctx.shadowOffsetX = 2;
      this.ctx.shadowOffsetY = 2;
      this.ctx.fillText(t.text, Math.round(t.x), Math.round(t.y));
      this.ctx.restore();
    }
  }

  /** Emits dark data elimination: binary shards & green eco-sparkles */
  emitDeletionPoof(x, y, count = 28) {
    for (let i = 0; i < count; i++) {
      const angle = (Math.PI * 2 * i) / count + (Math.random() - 0.5) * 0.5;
      const speed = 60 + Math.random() * 160;

      if (i % 2 === 0) {
        // Binary Shard (0 or 1)
        this.particles.push({
          type: "glyph",
          glyph: Math.random() > 0.5 ? "1" : "0",
          x: x,
          y: y,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed - 40,
          gravity: 120,
          drag: 0.94,
          size: 10 + Math.floor(Math.random() * 4),
          color: "#94a8b8",
          life: 0.7 + Math.random() * 0.4,
          maxLife: 1.0,
          hasFlutter: false,
        });
      } else {
        // Green Eco-Sparkle
        this.particles.push({
          type: "sparkle",
          x: x,
          y: y,
          vx: Math.cos(angle) * speed * 0.7,
          vy: -Math.abs(Math.sin(angle) * speed) - 50,
          gravity: -30, // Drift upward
          drag: 0.96,
          size: 3 + Math.floor(Math.random() * 3),
          color: Math.random() > 0.4 ? "#9be05c" : "#ffea78",
          life: 0.8 + Math.random() * 0.6,
          maxLife: 1.2,
          hasFlutter: true,
          flutterPhase: Math.random() * 10,
        });
      }
    }
  }

  /** Celebration Confetti Fountain */
  emitConfetti(x = window.innerWidth / 2, y = window.innerHeight * 0.8, count = 90) {
    const palette = ["#5cb339", "#ffea78", "#e04848", "#2288a6", "#ffaa5e", "#dcf59f"];
    for (let i = 0; i < count; i++) {
      const angle = -Math.PI / 2 + (Math.random() - 0.5) * 1.6;
      const speed = 200 + Math.random() * 320;
      this.particles.push({
        type: "pixel",
        x: x + (Math.random() - 0.5) * 40,
        y: y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        gravity: 280,
        drag: 0.97,
        size: 4 + Math.floor(Math.random() * 4),
        color: palette[Math.floor(Math.random() * palette.length)],
        life: 1.4 + Math.random() * 0.8,
        maxLife: 2.0,
        hasFlutter: true,
        flutterPhase: Math.random() * 10,
      });
    }
  }

  /** Floating score or carbon number */
  emitFloatingText(text, x, y, color = "#ffea78") {
    this.texts.push({
      text: text,
      x: x,
      y: y,
      vy: -40,
      color: color,
      scale: 1.0,
      life: 1.2,
      maxLife: 1.2,
    });
  }
}

// Global Particle Singleton
window.ParticleEngine = new RetroParticleEngine();
