/**
 * ARROW TRADE PRO 2.0 // Three.js Gamification & Ambient 3D Engine
 * Provides:
 *  1. Ambient 3D Market Depth Particle Grid (reacts to session P&L mood)
 *  2. 3D Rotating Rank Core Crystal in Top HUD
 *  3. 3D Celebration Particle Burst on Trade Wins, Rank Ups, Prop Passes & Payouts
 */
(function (window) {
  "use strict";

  class ThreeGamificationEngine {
    constructor() {
      this.available = typeof window.THREE !== "undefined";
      this.bgRenderer = null;
      this.bgScene = null;
      this.bgCamera = null;
      this.bgGrid = null;
      this.bgParticles = null;
      this.moodHue = 0.55; // Cyan-blue default
      this.targetHue = 0.55;

      this.rankRenderer = null;
      this.rankScene = null;
      this.rankCamera = null;
      this.rankMesh = null;
      this.rankBoost = 0;

      this.fxRenderer = null;
      this.fxScene = null;
      this.fxCamera = null;
      this.fxBursts = [];

      this._rafId = null;
      this._clock = this.available ? new window.THREE.Clock() : null;
    }

    init() {
      if (!this.available) {
        console.warn("Three.js not loaded; 3D gamification effects disabled.");
        return;
      }
      this._initAmbientBg();
      this._initRankBadge();
      this._initFxOverlay();
      this._startLoop();

      window.addEventListener("resize", () => this.onResize());
    }

    _createRenderer(canvas, alpha = true) {
      try {
        const renderer = new window.THREE.WebGLRenderer({
          canvas,
          alpha,
          antialias: true,
          powerPreference: "high-performance",
        });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        return renderer;
      } catch (e) {
        return null;
      }
    }

    _initAmbientBg() {
      const canvas = document.getElementById("three-bg-canvas");
      if (!canvas) return;
      const renderer = this._createRenderer(canvas, true);
      if (!renderer) return;

      this.bgRenderer = renderer;
      this.bgRenderer.setSize(window.innerWidth, window.innerHeight);

      const THREE = window.THREE;
      this.bgScene = new THREE.Scene();
      this.bgCamera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 200);
      this.bgCamera.position.set(0, 6, 18);
      this.bgCamera.lookAt(0, 0, 0);

      // Subtle wireframe wave plane
      const planeGeo = new THREE.PlaneGeometry(56, 36, 36, 22);
      planeGeo.rotateX(-Math.PI / 2.3);
      const planeMat = new THREE.MeshBasicMaterial({
        color: 0x38bdf8,
        wireframe: true,
        transparent: true,
        opacity: 0.065,
      });
      this.bgGrid = new THREE.Mesh(planeGeo, planeMat);
      this.bgGrid.position.set(0, -3.5, -6);
      this.bgGridBaseY = Float32Array.from(planeGeo.attributes.position.array);
      this.bgScene.add(this.bgGrid);

      // Floating market depth nodes
      const count = 110;
      const pos = new Float32Array(count * 3);
      for (let i = 0; i < count; i++) {
        pos[i * 3] = (Math.random() - 0.5) * 40;
        pos[i * 3 + 1] = (Math.random() - 0.5) * 18;
        pos[i * 3 + 2] = (Math.random() - 0.5) * 20 - 4;
      }
      const pGeo = new THREE.BufferGeometry();
      pGeo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
      const pMat = new THREE.PointsMaterial({
        color: 0x38bdf8,
        size: 0.14,
        transparent: true,
        opacity: 0.35,
      });
      this.bgParticles = new THREE.Points(pGeo, pMat);
      this.bgScene.add(this.bgParticles);
    }

    _initRankBadge() {
      const canvas = document.getElementById("three-rank-canvas");
      if (!canvas) return;
      const renderer = this._createRenderer(canvas, true);
      if (!renderer) return;

      this.rankRenderer = renderer;
      this.rankRenderer.setSize(42, 42);

      const THREE = window.THREE;
      this.rankScene = new THREE.Scene();
      this.rankCamera = new THREE.PerspectiveCamera(45, 1, 0.1, 50);
      this.rankCamera.position.set(0, 0, 3.4);

      const light1 = new THREE.DirectionalLight(0xffffff, 1.4);
      light1.position.set(3, 4, 5);
      this.rankScene.add(light1);

      const light2 = new THREE.PointLight(0x38bdf8, 1.8, 10);
      light2.position.set(-2, -2, 3);
      this.rankScene.add(light2);

      this.rankScene.add(new THREE.AmbientLight(0x94a3b8, 0.6));

      const geo = new THREE.OctahedronGeometry(1.05, 0);
      const mat = new THREE.MeshStandardMaterial({
        color: 0x38bdf8,
        emissive: 0x0ea5e9,
        emissiveIntensity: 0.35,
        metalness: 0.75,
        roughness: 0.18,
        flatShading: true,
      });
      this.rankMesh = new THREE.Mesh(geo, mat);
      this.rankScene.add(this.rankMesh);
    }

    _initFxOverlay() {
      const canvas = document.getElementById("three-fx-canvas");
      if (!canvas) return;
      const renderer = this._createRenderer(canvas, true);
      if (!renderer) return;

      this.fxRenderer = renderer;
      this.fxRenderer.setSize(window.innerWidth, window.innerHeight);

      const THREE = window.THREE;
      this.fxScene = new THREE.Scene();
      this.fxCamera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 100);
      this.fxCamera.position.set(0, 0, 14);
    }

    setMoodByPnl(pnl) {
      if (pnl > 0.01) {
        this.targetHue = 0.43; // Emerald
      } else if (pnl < -0.01) {
        this.targetHue = 0.96; // Rose
      } else {
        this.targetHue = 0.55; // Cyan
      }
    }

    setRankTier(rankName) {
      if (!this.rankMesh || !this.available) return;
      const THREE = window.THREE;
      const r = String(rankName || "").toLowerCase();
      let colorHex = 0x38bdf8;
      let emissiveHex = 0x0284c7;
      let newGeo = null;

      if (r.includes("wizard") || r.includes("legend") || r.includes("titan")) {
        colorHex = 0xf59e0b;
        emissiveHex = 0xd97706;
        newGeo = new THREE.TorusKnotGeometry(0.75, 0.24, 64, 12);
      } else if (r.includes("desk") || r.includes("quant") || r.includes("pro")) {
        colorHex = 0xa855f7;
        emissiveHex = 0x7e22ce;
        newGeo = new THREE.IcosahedronGeometry(1.05, 0);
      } else if (r.includes("scalper") || r.includes("funded")) {
        colorHex = 0x10b981;
        emissiveHex = 0x059669;
        newGeo = new THREE.DodecahedronGeometry(1.02, 0);
      }

      if (newGeo) {
        this.rankMesh.geometry.dispose();
        this.rankMesh.geometry = newGeo;
      }
      this.rankMesh.material.color.setHex(colorHex);
      this.rankMesh.material.emissive.setHex(emissiveHex);
      this.rankBoost = 1.8;
    }

    triggerCelebration(type = "win") {
      if (!this.fxScene || !this.available) return;
      const THREE = window.THREE;
      const palette =
        type === "payout" || type === "prop_pass"
          ? [0xf59e0b, 0x10b981, 0x38bdf8, 0xfde047]
          : type === "levelup"
          ? [0xa855f7, 0x38bdf8, 0xf59e0b]
          : [0x10b981, 0x34d399, 0x38bdf8];

      const shardCount = type === "win" ? 55 : 110;
      const group = new THREE.Group();
      const shards = [];

      for (let i = 0; i < shardCount; i++) {
        const size = 0.1 + Math.random() * 0.16;
        const geo = new THREE.OctahedronGeometry(size, 0);
        const mat = new THREE.MeshBasicMaterial({
          color: palette[i % palette.length],
          transparent: true,
          opacity: 0.95,
        });
        const mesh = new THREE.Mesh(geo, mat);
        mesh.position.set((Math.random() - 0.5) * 4, -2 + Math.random() * 2, (Math.random() - 0.5) * 2);
        const angle = Math.random() * Math.PI * 2;
        const speed = 4 + Math.random() * 7;
        shards.push({
          mesh,
          vx: Math.cos(angle) * speed * 0.7,
          vy: 4 + Math.random() * 7,
          vz: Math.sin(angle) * speed * 0.4,
          rx: (Math.random() - 0.5) * 8,
          ry: (Math.random() - 0.5) * 8,
        });
        group.add(mesh);
      }

      this.fxScene.add(group);
      this.fxBursts.push({ group, shards, age: 0, maxAge: 2.3 });
      this.rankBoost = 2.5;
    }

    onResize() {
      const w = window.innerWidth;
      const h = window.innerHeight;
      if (this.bgRenderer && this.bgCamera) {
        this.bgCamera.aspect = w / h;
        this.bgCamera.updateProjectionMatrix();
        this.bgRenderer.setSize(w, h);
      }
      if (this.fxRenderer && this.fxCamera) {
        this.fxCamera.aspect = w / h;
        this.fxCamera.updateProjectionMatrix();
        this.fxRenderer.setSize(w, h);
      }
    }

    _startLoop() {
      const animate = () => {
        this._rafId = requestAnimationFrame(animate);
        const dt = Math.min(this._clock.getDelta(), 0.05);
        const elapsed = this._clock.getElapsedTime();

        // 1. Ambient background wave + mood hue interpolation
        if (this.bgRenderer && this.bgScene && this.bgCamera) {
          this.moodHue += (this.targetHue - this.moodHue) * 0.04;
          if (this.bgGrid) {
            const posAttr = this.bgGrid.geometry.attributes.position;
            const base = this.bgGridBaseY;
            for (let i = 0; i < posAttr.count; i++) {
              const x = base[i * 3];
              const y = base[i * 3 + 1];
              posAttr.setZ(i, Math.sin(x * 0.25 + elapsed * 0.9) * 0.45 + Math.cos(y * 0.3 + elapsed * 0.7) * 0.45);
            }
            posAttr.needsUpdate = true;
            this.bgGrid.material.color.setHSL(this.moodHue, 0.85, 0.55);
          }
          if (this.bgParticles) {
            this.bgParticles.rotation.y = elapsed * 0.025;
            this.bgParticles.material.color.setHSL(this.moodHue, 0.9, 0.62);
          }
          this.bgRenderer.render(this.bgScene, this.bgCamera);
        }

        // 2. Rank 3D emblem
        if (this.rankRenderer && this.rankScene && this.rankCamera && this.rankMesh) {
          const speed = 0.8 + this.rankBoost * 3.0;
          this.rankMesh.rotation.y += dt * speed;
          this.rankMesh.rotation.x = Math.sin(elapsed * 1.1) * 0.25;
          this.rankBoost = Math.max(0, this.rankBoost - dt * 1.5);
          this.rankRenderer.render(this.rankScene, this.rankCamera);
        }

        // 3. Celebration FX particles
        if (this.fxRenderer && this.fxScene && this.fxCamera) {
          if (this.fxBursts.length > 0) {
            for (let b = this.fxBursts.length - 1; b >= 0; b--) {
              const burst = this.fxBursts[b];
              burst.age += dt;
              const fade = Math.max(0, 1 - burst.age / burst.maxAge);
              for (const s of burst.shards) {
                s.vy -= 9.5 * dt; // gravity
                s.mesh.position.x += s.vx * dt;
                s.mesh.position.y += s.vy * dt;
                s.mesh.position.z += s.vz * dt;
                s.mesh.rotation.x += s.rx * dt;
                s.mesh.rotation.y += s.ry * dt;
                s.mesh.material.opacity = fade;
              }
              if (burst.age >= burst.maxAge) {
                this.fxScene.remove(burst.group);
                burst.shards.forEach(s => {
                  s.mesh.geometry.dispose();
                  s.mesh.material.dispose();
                });
                this.fxBursts.splice(b, 1);
              }
            }
            this.fxRenderer.render(this.fxScene, this.fxCamera);
          } else {
            this.fxRenderer.clear();
          }
        }
      };
      animate();
    }
  }

  window.ThreeGamificationEngine = ThreeGamificationEngine;
})(window);
