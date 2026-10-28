/**
 * ==============================================================================
 * DATA-TO-DIRT — Procedural 5-Stage Growing Tree Visual Feedback Loop
 * Renders retro pixel-art tree stages: Soil -> Sprout -> Sapling -> Young Oak -> Ancient -> Golden
 * ==============================================================================
 */

class RetroTreeRenderer {
  constructor(canvasId = "tree-canvas") {
    this.canvasId = canvasId;
    this.canvas = null;
    this.ctx = null;
    this.currentStage = 0;
    this.progressPct = 0;
    this.stageName = "Prepared Soil";
    this.animTime = 0;
    this.isLevelingUp = false;
  }

  init() {
    this.canvas = document.getElementById(this.canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext("2d");
    this.resize();
    this.startLoop();
  }

  resize() {
    if (!this.canvas) return;
    const rect = this.canvas.parentElement.getBoundingClientRect();
    this.canvas.width = rect.width || 280;
    this.canvas.height = rect.height || 260;
  }

  setStage(stage, progressPct = 0, stageName = "") {
    if (stage > this.currentStage) {
      this.triggerLevelUp();
    }
    this.currentStage = Math.max(0, Math.min(5, stage));
    this.progressPct = progressPct;
    if (stageName) this.stageName = stageName;
  }

  triggerLevelUp() {
    this.isLevelingUp = true;
    if (window.RetroAudio) {
      window.RetroAudio.playVictoryFanfare();
    }
    if (window.ParticleEngine && this.canvas) {
      const rect = this.canvas.getBoundingClientRect();
      window.ParticleEngine.emitConfetti(rect.left + rect.width / 2, rect.top + rect.height / 2, 70);
    }
    setTimeout(() => {
      this.isLevelingUp = false;
    }, 1200);
  }

  startLoop() {
    const loop = (t) => {
      this.animTime = t / 1000.0;
      this.render();
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  render() {
    if (!this.ctx || !this.canvas) return;
    const w = this.canvas.width;
    const h = this.canvas.height;
    const ctx = this.ctx;

    ctx.clearRect(0, 0, w, h);

    // Baseline grass soil ground
    const groundY = h - 36;
    this.drawGround(ctx, w, groundY);

    // Draw tree based on stage
    ctx.save();
    if (this.isLevelingUp) {
      const bounce = Math.sin(this.animTime * 15) * 4;
      ctx.translate(0, bounce);
    }

    const centerX = w / 2;

    switch (this.currentStage) {
      case 0:
        this.drawStage0_Soil(ctx, centerX, groundY);
        break;
      case 1:
        this.drawStage1_Sprout(ctx, centerX, groundY);
        break;
      case 2:
        this.drawStage2_Sapling(ctx, centerX, groundY);
        break;
      case 3:
        this.drawStage3_YoungOak(ctx, centerX, groundY);
        break;
      case 4:
        this.drawStage4_AncientTree(ctx, centerX, groundY);
        break;
      case 5:
        this.drawStage5_GoldenTree(ctx, centerX, groundY);
        break;
    }
    ctx.restore();
  }

  drawGround(ctx, w, groundY) {
    // Soil mound base
    ctx.fillStyle = "#3b200b";
    ctx.fillRect(0, groundY + 4, w, 32);

    // Grass topper
    ctx.fillStyle = "#265c2a";
    ctx.fillRect(0, groundY, w, 4);

    // Pixel grass tufts
    ctx.fillStyle = "#439235";
    for (let x = 12; x < w - 12; x += 24) {
      ctx.fillRect(x, groundY - 4, 3, 4);
      ctx.fillRect(x + 3, groundY - 2, 2, 2);
    }
  }

  /** Stage 0: Prepared Soil Mound with wooden sign */
  drawStage0_Soil(ctx, cx, gy) {
    // Fresh tilled mound
    ctx.fillStyle = "#4a2c13";
    ctx.beginPath();
    ctx.ellipse(cx, gy, 48, 12, 0, 0, Math.PI * 2);
    ctx.fill();

    // Wooden sign post
    ctx.fillStyle = "#633d1c";
    ctx.fillRect(cx - 3, gy - 36, 6, 36);

    // Wooden sign board
    ctx.fillStyle = "#875529";
    ctx.fillRect(cx - 32, gy - 58, 64, 22);
    ctx.fillStyle = "#2a1508";
    ctx.strokeRect(cx - 32, gy - 58, 64, 22);

    // Sign text
    ctx.fillStyle = "#f8f1de";
    ctx.font = 'bold 9px "Courier New", monospace';
    ctx.textAlign = "center";
    ctx.fillText("PLANT DATA", cx, gy - 44);
  }

  /** Stage 1: The Sprout */
  drawStage1_Sprout(ctx, cx, gy) {
    const sway = Math.sin(this.animTime * 2.5) * 2;

    // Stem
    ctx.fillStyle = "#5cb339";
    ctx.fillRect(cx - 2, gy - 24, 4, 24);

    // Left Leaf
    ctx.fillStyle = "#9be05c";
    ctx.beginPath();
    ctx.ellipse(cx - 8 + sway, gy - 24, 8, 4, -0.4, 0, Math.PI * 2);
    ctx.fill();

    // Right Leaf
    ctx.fillStyle = "#439235";
    ctx.beginPath();
    ctx.ellipse(cx + 8 + sway, gy - 28, 9, 4, 0.4, 0, Math.PI * 2);
    ctx.fill();

    // Dewdrop sparkle
    ctx.fillStyle = "#e6f3fc";
    ctx.fillRect(cx + 10 + sway, gy - 30, 2, 2);
  }

  /** Stage 2: The Sapling */
  drawStage2_Sapling(ctx, cx, gy) {
    const sway = Math.sin(this.animTime * 2.0) * 3;

    // Trunk
    ctx.fillStyle = "#633d1c";
    ctx.fillRect(cx - 4, gy - 65, 8, 65);

    // Branches
    ctx.fillRect(cx - 16, gy - 45, 14, 4);
    ctx.fillRect(cx + 4, gy - 52, 16, 4);

    // Foliage Clusters
    ctx.fillStyle = "#37802b";
    this.drawPixelCircle(ctx, cx - 18 + sway, gy - 48, 14);
    this.drawPixelCircle(ctx, cx + 18 + sway, gy - 56, 16);

    ctx.fillStyle = "#5cb339";
    this.drawPixelCircle(ctx, cx + sway, gy - 74, 20);

    // Highlights
    ctx.fillStyle = "#9be05c";
    ctx.fillRect(cx + sway - 6, gy - 82, 10, 6);
  }

  /** Stage 3: Young Oak */
  drawStage3_YoungOak(ctx, cx, gy) {
    const sway = Math.sin(this.animTime * 1.6) * 3;

    // Wide trunk
    ctx.fillStyle = "#4d2d14";
    ctx.fillRect(cx - 9, gy - 110, 18, 110);
    // Root flares
    ctx.fillRect(cx - 16, gy - 12, 8, 12);
    ctx.fillRect(cx + 8, gy - 12, 8, 12);

    // Dark foliage mass
    ctx.fillStyle = "#1e4a23";
    this.drawPixelCircle(ctx, cx + sway, gy - 120, 48);
    this.drawPixelCircle(ctx, cx - 30 + sway, gy - 100, 36);
    this.drawPixelCircle(ctx, cx + 30 + sway, gy - 105, 38);

    // Bright foliage layer
    ctx.fillStyle = "#37802b";
    this.drawPixelCircle(ctx, cx + sway - 5, gy - 125, 40);
    this.drawPixelCircle(ctx, cx - 24 + sway, gy - 105, 30);
    this.drawPixelCircle(ctx, cx + 24 + sway, gy - 110, 32);

    // Leaf Highlights
    ctx.fillStyle = "#9be05c";
    this.drawPixelCircle(ctx, cx + sway - 8, gy - 145, 16);
    this.drawPixelCircle(ctx, cx + sway + 14, gy - 130, 14);
  }

  /** Stage 4: Ancient Tree */
  drawStage4_AncientTree(ctx, cx, gy) {
    const sway = Math.sin(this.animTime * 1.2) * 2;

    // Deep Gnarled Trunk
    ctx.fillStyle = "#3b200b";
    ctx.fillRect(cx - 18, gy - 140, 36, 140);
    ctx.fillRect(cx - 28, gy - 20, 14, 20);
    ctx.fillRect(cx + 14, gy - 20, 16, 20);

    // Hollow / Knothole
    ctx.fillStyle = "#1c0d03";
    ctx.fillRect(cx - 4, gy - 60, 8, 12);

    // Massive Canopy
    ctx.fillStyle = "#163a1a";
    this.drawPixelCircle(ctx, cx + sway, gy - 155, 68);
    this.drawPixelCircle(ctx, cx - 45 + sway, gy - 130, 52);
    this.drawPixelCircle(ctx, cx + 45 + sway, gy - 135, 54);

    ctx.fillStyle = "#265c2a";
    this.drawPixelCircle(ctx, cx + sway, gy - 165, 58);
    this.drawPixelCircle(ctx, cx - 38 + sway, gy - 140, 44);
    this.drawPixelCircle(ctx, cx + 38 + sway, gy - 145, 46);

    ctx.fillStyle = "#5cb339";
    this.drawPixelCircle(ctx, cx + sway - 12, gy - 180, 34);
    this.drawPixelCircle(ctx, cx + 24 + sway, gy - 165, 28);

    // Animated Squirrel / Robin
    const birdY = gy - 100 + Math.sin(this.animTime * 4) * 2;
    ctx.fillStyle = "#e04848"; // Cardinal red bird
    ctx.fillRect(cx + 26, birdY, 6, 5);
    ctx.fillStyle = "#ffea78";
    ctx.fillRect(cx + 32, birdY + 2, 2, 2);
  }

  /** Stage 5: Legendary Golden Tree */
  drawStage5_GoldenTree(ctx, cx, gy) {
    const sway = Math.sin(this.animTime * 1.0) * 3;

    // Radiant Gold Trunk
    ctx.fillStyle = "#805215";
    ctx.fillRect(cx - 22, gy - 150, 44, 150);
    ctx.fillStyle = "#b87714";
    ctx.fillRect(cx - 16, gy - 145, 8, 140);

    // Glowing Golden Canopy
    ctx.fillStyle = "#b87714";
    this.drawPixelCircle(ctx, cx + sway, gy - 165, 74);
    this.drawPixelCircle(ctx, cx - 50 + sway, gy - 140, 56);
    this.drawPixelCircle(ctx, cx + 50 + sway, gy - 145, 58);

    ctx.fillStyle = "#e8a72b";
    this.drawPixelCircle(ctx, cx + sway, gy - 175, 62);
    this.drawPixelCircle(ctx, cx - 40 + sway, gy - 150, 48);
    this.drawPixelCircle(ctx, cx + 40 + sway, gy - 155, 50);

    ctx.fillStyle = "#ffea78";
    this.drawPixelCircle(ctx, cx + sway - 10, gy - 195, 36);
    this.drawPixelCircle(ctx, cx + 25 + sway, gy - 180, 30);

    // Golden Apples / Orbs
    const apples = [
      { x: cx - 25, y: gy - 160 },
      { x: cx + 30, y: gy - 175 },
      { x: cx - 5, y: gy - 190 },
      { x: cx + 15, y: gy - 145 },
    ];

    apples.forEach((a) => {
      const pulse = Math.sin(this.animTime * 5 + a.x) * 1.5;
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(a.x + sway - 1, a.y - 1, 6 + pulse, 6 + pulse);
      ctx.fillStyle = "#ffea78";
      ctx.fillRect(a.x + sway, a.y, 4 + pulse, 4 + pulse);
    });

    // Falling Golden Blossom Petals
    ctx.fillStyle = "#fff59d";
    for (let i = 0; i < 6; i++) {
      const px = cx - 70 + ((this.animTime * 25 + i * 35) % 140);
      const py = gy - 200 + ((this.animTime * 40 + i * 45) % 180);
      ctx.fillRect(Math.round(px), Math.round(py), 3, 3);
    }
  }

  drawPixelCircle(ctx, cx, cy, r) {
    ctx.beginPath();
    ctx.arc(Math.round(cx), Math.round(cy), Math.round(r), 0, Math.PI * 2);
    ctx.fill();
  }
}

// Global Tree Renderer Singleton
window.TreeRenderer = new RetroTreeRenderer();
