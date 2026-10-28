"use client";

import React, { useEffect, useRef } from "react";
import * as THREE from "three";

/* ═══════════════════════════════════════════════════════════════════
   DHWANI AI NEURAL CORE — COLOR PALETTE (EXACT SPECIFICATION)
   Predominantly dark (60–70% dark body) + electric purple & blue rim highlights
   ═══════════════════════════════════════════════════════════════════ */
const PALETTE = {
  black: 0x05030d,
  darkNavy: 0x080a1f,
  deepIndigo: 0x11104a,
  violet: 0x6d28d9,
  electricPurple: 0x8b5cf6,
  magenta: 0xc026d3,
  electricBlue: 0x2563eb,
  cyanAccents: 0x00d9ff,
  pureWhite: 0xffffff,
};

interface DhwaniSphereProps {
  className?: string;
  speed?: number;
}

export default function DhwaniSphere({
  className = "",
  speed = 1,
}: DhwaniSphereProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const frameRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    // ═════════════════════════════════════════════
    //  RENDERER — 100% TRANSPARENT CANVAS
    // ═════════════════════════════════════════════
    const isMobile = window.innerWidth < 768;
    const dpr = Math.min(window.devicePixelRatio, isMobile ? 1.5 : 2);

    const renderer = new THREE.WebGLRenderer({
      canvas,
      alpha: true,
      antialias: true,
      powerPreference: "high-performance",
    });
    renderer.setPixelRatio(dpr);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.35; // Calibrated for deep rich blacks and crisp rim highlights
    renderer.setClearColor(0x000000, 0);

    // ═════════════════════════════════════════════
    //  SCENE & CAMERA
    // ═════════════════════════════════════════════
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 50);
    camera.position.set(0, 0, 6.4);

    const handleResize = () => {
      const w = container.clientWidth || 360;
      const h = container.clientHeight || 360;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    handleResize();

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(container);
    window.addEventListener("resize", handleResize);

    // ═════════════════════════════════════════════
    //  HDR CYBERPUNK ENVIRONMENT MAP
    //  Creates razor-sharp purple and cyan specular edge reflections on dark chrome
    // ═════════════════════════════════════════════
    const cubeRenderTarget = new THREE.WebGLCubeRenderTarget(256, {
      generateMipmaps: true,
      minFilter: THREE.LinearMipmapLinearFilter,
      magFilter: THREE.LinearFilter,
    });
    const cubeCamera = new THREE.CubeCamera(0.1, 10, cubeRenderTarget);

    const envScene = new THREE.Scene();
    const envBoxGeo = new THREE.BoxGeometry(10, 10, 10);
    const envMaterials = [
      new THREE.MeshBasicMaterial({ color: PALETTE.cyanAccents }), // right: cyan
      new THREE.MeshBasicMaterial({ color: PALETTE.electricPurple }), // left: purple
      new THREE.MeshBasicMaterial({ color: PALETTE.violet }), // top: violet
      new THREE.MeshBasicMaterial({ color: PALETTE.black }), // bottom: pure dark shadow
      new THREE.MeshBasicMaterial({ color: PALETTE.pureWhite }), // front: pinpoint white glint
      new THREE.MeshBasicMaterial({ color: PALETTE.deepIndigo }), // back: deep indigo
    ];
    const envMesh = new THREE.Mesh(envBoxGeo, envMaterials);
    envMesh.material.forEach((m) => (m.side = THREE.BackSide));
    envScene.add(envMesh);
    cubeCamera.update(renderer, envScene);
    scene.environment = cubeRenderTarget.texture;

    // ═════════════════════════════════════════════
    //  CINEMATIC LIGHTING RIG
    //  High-contrast mood lighting: dark surfaces, sharp colored rim glints
    // ═════════════════════════════════════════════
    scene.add(new THREE.AmbientLight(PALETTE.darkNavy, 1.4));

    // Key Light 1: Deep Violet / Electric Purple (upper-left)
    const purpleKeyLight = new THREE.DirectionalLight(PALETTE.electricPurple, 6.0);
    purpleKeyLight.position.set(-5, 6, 4.5);
    scene.add(purpleKeyLight);

    // Key Light 2: Electric Blue (bottom-right)
    const blueKeyLight = new THREE.DirectionalLight(PALETTE.electricBlue, 5.0);
    blueKeyLight.position.set(5.5, -4.5, 4);
    scene.add(blueKeyLight);

    // Rim Light: Vivid Cyan Accent (back-right edge)
    const cyanRimLight = new THREE.DirectionalLight(PALETTE.cyanAccents, 4.5);
    cyanRimLight.position.set(4, 2.5, -5);
    scene.add(cyanRimLight);

    // Specular Glint Light: Sharp pinpoint white highlight for beveled chamfers
    const glintLight = new THREE.PointLight(PALETTE.pureWhite, 3.5, 12);
    glintLight.position.set(2, 3, 5);
    scene.add(glintLight);

    // ═════════════════════════════════════════════
    //  MASTER ORB ROOT GROUP
    // ═════════════════════════════════════════════
    const orbGroup = new THREE.Group();
    scene.add(orbGroup);

    // ═════════════════════════════════════════════
    //  1. INNER AI NEURAL CORE
    //  Dark spherical core with digital particle lattice, concentric rings,
    //  and a concentrated pinpoint violet/cyan energy flare at center
    // ═════════════════════════════════════════════
    const coreGroup = new THREE.Group();
    orbGroup.add(coreGroup);

    // ── Dark Spherical Glass Base ──
    const innerCoreGeo = new THREE.SphereGeometry(0.66, 36, 36);
    const innerCoreMat = new THREE.MeshPhysicalMaterial({
      color: PALETTE.black,
      emissive: PALETTE.deepIndigo,
      emissiveIntensity: 0.35,
      roughness: 0.12,
      metalness: 0.85,
      clearcoat: 1.0,
      clearcoatRoughness: 0.03,
      transmission: 0.25,
      ior: 1.6,
      envMap: cubeRenderTarget.texture,
      envMapIntensity: 3.0,
    });
    const innerCoreMesh = new THREE.Mesh(innerCoreGeo, innerCoreMat);
    coreGroup.add(innerCoreMesh);

    // ── Digital Neural Particle Mesh (Grid of glowing dots on sphere) ──
    const neuralDotsPositions: number[] = [];
    const neuralDotsColors: number[] = [];
    const latCount = 26;
    const lonCount = 42;
    const coreRadius = 0.675;

    const colViolet = new THREE.Color(PALETTE.violet);
    const colPurple = new THREE.Color(PALETTE.electricPurple);
    const colCyan = new THREE.Color(PALETTE.cyanAccents);

    for (let i = 1; i < latCount; i++) {
      const phi = (i / latCount) * Math.PI;
      const countAtLat = Math.max(8, Math.floor(lonCount * Math.sin(phi)));
      for (let j = 0; j < countAtLat; j++) {
        const theta = (j / countAtLat) * Math.PI * 2;
        const x = coreRadius * Math.sin(phi) * Math.cos(theta);
        const y = coreRadius * Math.cos(phi);
        const z = coreRadius * Math.sin(phi) * Math.sin(theta);
        neuralDotsPositions.push(x, y, z);

        // Gradient coloring: cyan accents at equator, electric purple & violet towards poles
        const latNorm = Math.abs(Math.cos(phi));
        const c = latNorm < 0.25 ? colCyan : latNorm < 0.6 ? colPurple : colViolet;
        neuralDotsColors.push(c.r, c.g, c.b);
      }
    }

    const neuralDotsGeo = new THREE.BufferGeometry();
    neuralDotsGeo.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(neuralDotsPositions, 3)
    );
    neuralDotsGeo.setAttribute(
      "color",
      new THREE.Float32BufferAttribute(neuralDotsColors, 3)
    );

    const neuralDotsMat = new THREE.PointsMaterial({
      size: isMobile ? 0.016 : 0.022,
      vertexColors: true,
      transparent: true,
      opacity: 0.9,
      blending: THREE.AdditiveBlending,
    });
    const neuralDotsMesh = new THREE.Points(neuralDotsGeo, neuralDotsMat);
    coreGroup.add(neuralDotsMesh);

    // ── Concentric Neural Lattice Rings ──
    [-0.32, 0, 0.32].forEach((yOffset) => {
      const ringRad = Math.sqrt(Math.max(0, coreRadius * coreRadius - yOffset * yOffset));
      const ringGeo = new THREE.RingGeometry(ringRad - 0.004, ringRad + 0.004, 48);
      const ringMat = new THREE.MeshBasicMaterial({
        color: PALETTE.electricPurple,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.45,
        blending: THREE.AdditiveBlending,
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.x = Math.PI / 2;
      ring.position.y = yOffset;
      coreGroup.add(ring);
    });

    // ── Center Deep Violet / Cyan Pinpoint Energy Flare ──
    const centerPointLight1 = new THREE.PointLight(PALETTE.electricPurple, 9.0, 4.5);
    centerPointLight1.position.set(0, 0, 0);
    coreGroup.add(centerPointLight1);

    const centerPointLight2 = new THREE.PointLight(PALETTE.cyanAccents, 5.0, 3.5);
    centerPointLight2.position.set(0.1, 0.1, 0.1);
    coreGroup.add(centerPointLight2);

    const flareGeo = new THREE.SphereGeometry(0.14, 20, 20);
    const flareMat = new THREE.MeshBasicMaterial({
      color: PALETTE.magenta,
      transparent: true,
      opacity: 0.95,
      blending: THREE.AdditiveBlending,
    });
    const flareMesh = new THREE.Mesh(flareGeo, flareMat);
    coreGroup.add(flareMesh);

    // ═════════════════════════════════════════════
    //  2. INTERLOCKING AERODYNAMIC RIBBON BANDS (8–12 BANDS)
    //  Flat, beveled aerodynamic bands wrapping organically around the core.
    //  Dark metallic surfaces (60–70% dark) catching sharp purple/blue rim light.
    // ═════════════════════════════════════════════
    const ribbonsGroup = new THREE.Group();
    orbGroup.add(ribbonsGroup);

    // Helper: Creates flat, chamfered aerodynamic ribbon band geometries
    function createAerodynamicBandGeometry(
      radius: number,
      width: number,
      thickness: number,
      waveAmp: number = 0,
      waveFreq: number = 2,
      steps: number = 54
    ) {
      const shape = new THREE.Shape();
      const w = width;
      const h = thickness;
      const b = thickness * 0.32; // Chamfered beveled edges

      // 8-point beveled chamfer cross-section (aerodynamic band profile)
      shape.moveTo(-w / 2 + b, -h / 2);
      shape.lineTo(w / 2 - b, -h / 2);
      shape.lineTo(w / 2, -h / 2 + b);
      shape.lineTo(w / 2, h / 2 - b);
      shape.lineTo(w / 2 - b, h / 2);
      shape.lineTo(-w / 2 + b, h / 2);
      shape.lineTo(-w / 2, h / 2 - b);
      shape.lineTo(-w / 2, -h / 2 + b);
      shape.closePath();

      const points: THREE.Vector3[] = [];
      for (let i = 0; i <= steps; i++) {
        const theta = (i / steps) * Math.PI * 2;
        const r = radius + (waveAmp > 0 ? Math.sin(theta * waveFreq) * waveAmp : 0);
        const z = waveAmp > 0 ? Math.cos(theta * waveFreq) * (waveAmp * 1.4) : 0;
        points.push(new THREE.Vector3(Math.cos(theta) * r, Math.sin(theta) * r, z));
      }
      const curve = new THREE.CatmullRomCurve3(points, true, "centripetal");

      const geo = new THREE.ExtrudeGeometry(shape, {
        extrudePath: curve,
        steps,
        bevelEnabled: false,
      });
      geo.computeVertexNormals();
      return geo;
    }

    // Material 1: Dark Polished Chrome (Deep black/navy body with sharp specular reflections)
    const darkChromeMat = new THREE.MeshPhysicalMaterial({
      color: PALETTE.black,
      emissive: PALETTE.deepIndigo,
      emissiveIntensity: 0.16,
      metalness: 0.98,
      roughness: 0.04,
      clearcoat: 1.0,
      clearcoatRoughness: 0.015,
      iridescence: 0.9,
      iridescenceIOR: 1.85,
      iridescenceThicknessRange: [100, 380],
      envMap: cubeRenderTarget.texture,
      envMapIntensity: 4.8,
      side: THREE.DoubleSide,
    });

    // Material 2: Smoked Cyberpunk Glass (Translucent dark violet glass)
    const smokedGlassMat = new THREE.MeshPhysicalMaterial({
      color: PALETTE.darkNavy,
      emissive: PALETTE.violet,
      emissiveIntensity: 0.22,
      metalness: 0.2,
      roughness: 0.025,
      transmission: 0.72,
      transparent: true,
      opacity: 0.94,
      ior: 1.62,
      thickness: 1.4,
      attenuationColor: new THREE.Color(PALETTE.violet),
      attenuationDistance: 0.85,
      clearcoat: 1.0,
      clearcoatRoughness: 0.02,
      envMap: cubeRenderTarget.texture,
      envMapIntensity: 4.2,
      side: THREE.DoubleSide,
    });

    // Material 3: Deep Indigo Reflective Metal with Blue Rim Sheen
    const deepIndigoMat = new THREE.MeshPhysicalMaterial({
      color: PALETTE.deepIndigo,
      emissive: PALETTE.electricBlue,
      emissiveIntensity: 0.24,
      metalness: 0.95,
      roughness: 0.05,
      clearcoat: 1.0,
      clearcoatRoughness: 0.02,
      iridescence: 0.92,
      iridescenceIOR: 1.75,
      iridescenceThicknessRange: [120, 420],
      envMap: cubeRenderTarget.texture,
      envMapIntensity: 4.4,
      side: THREE.DoubleSide,
    });

    // Configuration for the 10 interlocking aerodynamic bands
    const bandConfigs = [
      // 1. Prominent Foreground Armillary Gimbal Ring (Major visual anchor matching reference)
      { r: 1.28, w: 0.27, t: 0.055, rot: [0.82, 0.42, -0.22], amp: 0, mat: darkChromeMat, group: "A" },
      // 2. Interlocking Cross-Axis Smoked Glass Ring (Translucent overlap)
      { r: 1.24, w: 0.23, t: 0.048, rot: [-0.65, -0.52, 0.85], amp: 0.06, mat: smokedGlassMat, group: "B" },
      // 3. Steep Diagonal Dark Chrome Band (Frames top-right)
      { r: 1.21, w: 0.22, t: 0.046, rot: [1.25, -0.68, 0.35], amp: 0, mat: deepIndigoMat, group: "A" },
      // 4. Counter-Tilted Metallic Band (Weaves behind ribbon 1)
      { r: 1.18, w: 0.20, t: 0.045, rot: [-0.28, 1.15, -0.88], amp: 0.05, mat: darkChromeMat, group: "B" },
      // 5. Equatorial Wide Band (Anchors bottom-left to top-right)
      { r: 1.30, w: 0.20, t: 0.044, rot: [0.35, -0.88, 1.28], amp: 0, mat: smokedGlassMat, group: "A" },
      // 6. Deep Interior Framing Band (Wraps tightly around neural core)
      { r: 1.14, w: 0.22, t: 0.048, rot: [-1.12, 0.24, -0.58], amp: 0.06, mat: darkChromeMat, group: "B" },
      // 7. Middle Orbital Stabilizer Band
      { r: 1.12, w: 0.24, t: 0.046, rot: [0.52, 1.22, 0.42], amp: 0, mat: deepIndigoMat, group: "A" },
      // 8. Rear Dark Background Shield Band (Adds deep shadow occlusion)
      { r: 1.15, w: 0.19, t: 0.042, rot: [-0.44, -1.05, -0.72], amp: 0.04, mat: darkChromeMat, group: "B" },
      // 9. Flowing Fluid Wave Ribbon (Dynamic aerodynamic S-curve)
      { r: 1.26, w: 0.16, t: 0.038, rot: [0.92, -0.32, 0.74], amp: 0.08, mat: smokedGlassMat, group: "A" },
      // 10. Outer Framing Cyan Accent Band
      { r: 1.22, w: 0.17, t: 0.040, rot: [-0.75, 0.65, -1.15], amp: 0.05, mat: deepIndigoMat, group: "B" },
    ];

    const groupRibbonsA = new THREE.Group();
    const groupRibbonsB = new THREE.Group();
    ribbonsGroup.add(groupRibbonsA);
    ribbonsGroup.add(groupRibbonsB);

    bandConfigs.forEach((cfg) => {
      const geo = createAerodynamicBandGeometry(cfg.r, cfg.w, cfg.t, cfg.amp);
      const mesh = new THREE.Mesh(geo, cfg.mat);
      mesh.rotation.set(cfg.rot[0], cfg.rot[1], cfg.rot[2]);
      if (cfg.group === "A") {
        groupRibbonsA.add(mesh);
      } else {
        groupRibbonsB.add(mesh);
      }
    });

    // ── Glowing Neon Edge Lines for the Foreground Ribbon ──
    // Lower/outer edge: Cyan glow
    const edgePoints1: THREE.Vector3[] = [];
    // Upper/inner edge: Purple glow
    const edgePoints2: THREE.Vector3[] = [];
    for (let i = 0; i <= 64; i++) {
      const theta = (i / 64) * Math.PI * 2;
      edgePoints1.push(
        new THREE.Vector3(
          Math.cos(theta) * 1.285,
          Math.sin(theta) * 1.285,
          0.028
        )
      );
      edgePoints2.push(
        new THREE.Vector3(
          Math.cos(theta) * 1.275,
          Math.sin(theta) * 1.275,
          -0.028
        )
      );
    }
    const edgeCurve1 = new THREE.CatmullRomCurve3(edgePoints1, true);
    const edgeGeo1 = new THREE.TubeGeometry(edgeCurve1, 64, 0.007, 8, true);
    const edgeMat1 = new THREE.MeshBasicMaterial({
      color: PALETTE.cyanAccents,
      transparent: true,
      opacity: 0.85,
    });
    const edgeMesh1 = new THREE.Mesh(edgeGeo1, edgeMat1);
    edgeMesh1.rotation.set(0.82, 0.42, -0.22);
    groupRibbonsA.add(edgeMesh1);

    const edgeCurve2 = new THREE.CatmullRomCurve3(edgePoints2, true);
    const edgeGeo2 = new THREE.TubeGeometry(edgeCurve2, 64, 0.007, 8, true);
    const edgeMat2 = new THREE.MeshBasicMaterial({
      color: PALETTE.electricPurple,
      transparent: true,
      opacity: 0.85,
    });
    const edgeMesh2 = new THREE.Mesh(edgeGeo2, edgeMat2);
    edgeMesh2.rotation.set(0.82, 0.42, -0.22);
    groupRibbonsA.add(edgeMesh2);

    // ═════════════════════════════════════════════
    //  3. ULTRA-THIN ORBITAL RINGS & GLOWING NODES (2–4 RINGS)
    //  Delicate glowing lines with tiny orbiting data node beads
    // ═════════════════════════════════════════════
    const orbitalGroup = new THREE.Group();
    orbGroup.add(orbitalGroup);

    interface OrbitalRingConfig {
      radius: number;
      color: number;
      rot: [number, number, number];
      nodeCount: number;
      speed: number;
    }

    const orbitalConfigs: OrbitalRingConfig[] = [
      // Ring 1: Cyan Horizontal-Diagonal Orbit with 2 nodes
      { radius: 1.58, color: PALETTE.cyanAccents, rot: [1.32, 0.22, -0.38], nodeCount: 2, speed: 0.6 },
      // Ring 2: Electric Purple Steep Orbit with 2 nodes
      { radius: 1.48, color: PALETTE.electricPurple, rot: [-0.55, 0.82, 0.64], nodeCount: 2, speed: -0.45 },
      // Ring 3: Deep Electric Blue Outer Orbit with 1 node
      { radius: 1.66, color: PALETTE.electricBlue, rot: [0.32, -1.12, 0.78], nodeCount: 1, speed: 0.35 },
    ];

    const orbitalNodes: { mesh: THREE.Mesh; ringRadius: number; angle: number; speed: number; parentGroup: THREE.Group }[] = [];

    orbitalConfigs.forEach((cfg) => {
      const ringGroup = new THREE.Group();
      ringGroup.rotation.set(cfg.rot[0], cfg.rot[1], cfg.rot[2]);
      orbitalGroup.add(ringGroup);

      // Razor-thin glowing line
      const ringGeo = new THREE.TorusGeometry(cfg.radius, 0.0065, 12, 100);
      const ringMat = new THREE.MeshBasicMaterial({
        color: cfg.color,
        transparent: true,
        opacity: 0.7,
        blending: THREE.AdditiveBlending,
      });
      const ringMesh = new THREE.Mesh(ringGeo, ringMat);
      ringGroup.add(ringMesh);

      // Glowing node beads on the orbital ring
      for (let i = 0; i < cfg.nodeCount; i++) {
        const nodeGeo = new THREE.SphereGeometry(0.026, 16, 16);
        const nodeMat = new THREE.MeshBasicMaterial({
          color: cfg.color,
          blending: THREE.AdditiveBlending,
        });
        const nodeMesh = new THREE.Mesh(nodeGeo, nodeMat);
        const startAngle = (i / cfg.nodeCount) * Math.PI * 2;
        nodeMesh.position.set(
          Math.cos(startAngle) * cfg.radius,
          Math.sin(startAngle) * cfg.radius,
          0
        );
        ringGroup.add(nodeMesh);

        orbitalNodes.push({
          mesh: nodeMesh,
          ringRadius: cfg.radius,
          angle: startAngle,
          speed: cfg.speed * 0.012,
          parentGroup: ringGroup,
        });
      }
    });

    // ═════════════════════════════════════════════
    //  4. SUBTLE AMBIENT CYBER PARTICLES
    //  A restrained constellation of tiny glowing dots (purple, blue, cyan)
    // ═════════════════════════════════════════════
    const particleCount = 55;
    const particleGeo = new THREE.BufferGeometry();
    const particlePositions = new Float32Array(particleCount * 3);
    const particleColors = new Float32Array(particleCount * 3);

    const pColPurple = new THREE.Color(PALETTE.electricPurple);
    const pColCyan = new THREE.Color(PALETTE.cyanAccents);
    const pColBlue = new THREE.Color(PALETTE.electricBlue);

    for (let i = 0; i < particleCount; i++) {
      const rad = 1.35 + Math.random() * 1.25;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(Math.random() * 2 - 1);

      particlePositions[i * 3] = rad * Math.sin(phi) * Math.cos(theta);
      particlePositions[i * 3 + 1] = rad * Math.cos(phi);
      particlePositions[i * 3 + 2] = rad * Math.sin(phi) * Math.sin(theta);

      const rand = Math.random();
      const col = rand < 0.45 ? pColPurple : rand < 0.75 ? pColCyan : pColBlue;
      particleColors[i * 3] = col.r;
      particleColors[i * 3 + 1] = col.g;
      particleColors[i * 3 + 2] = col.b;
    }

    particleGeo.setAttribute("position", new THREE.BufferAttribute(particlePositions, 3));
    particleGeo.setAttribute("color", new THREE.BufferAttribute(particleColors, 3));

    const particleMat = new THREE.PointsMaterial({
      size: isMobile ? 0.024 : 0.032,
      vertexColors: true,
      transparent: true,
      opacity: 0.65,
      blending: THREE.AdditiveBlending,
    });
    const particles = new THREE.Points(particleGeo, particleMat);
    scene.add(particles);

    // ═════════════════════════════════════════════
    //  MOUSE PARALLAX INTERACTION
    // ═════════════════════════════════════════════
    let targetRotX = 0;
    let targetRotY = 0;

    const onMouseMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      const clientX = e.clientX - rect.left;
      const clientY = e.clientY - rect.top;
      targetRotY = ((clientX / rect.width) * 2 - 1) * 0.35;
      targetRotX = (-((clientY / rect.height) * 2 - 1)) * 0.28;
    };
    window.addEventListener("mousemove", onMouseMove);

    // ═════════════════════════════════════════════
    //  CONTINUOUS CINEMATIC ROTATION ANIMATION
    //  Slow, sophisticated rotational choreography reflecting an active AI neural reactor
    // ═════════════════════════════════════════════
    let time = 0;
    const animate = () => {
      frameRef.current = requestAnimationFrame(animate);
      time += 0.0055 * speed;

      // Group A Ribbon Bands (very slow, majestic forward roll)
      groupRibbonsA.rotation.y = time * 0.35;
      groupRibbonsA.rotation.x = Math.sin(time * 0.25) * 0.12;

      // Group B Ribbon Bands (counter-rotational weave)
      groupRibbonsB.rotation.y = -time * 0.28;
      groupRibbonsB.rotation.x = Math.cos(time * 0.22) * 0.14;

      // Inner Core: subtle independent rotation
      coreGroup.rotation.y = time * 0.45;
      coreGroup.rotation.z = Math.sin(time * 0.3) * 0.08;

      // Inner Core AI Breathing Pulse
      const pulse = 1 + Math.sin(time * 2.0) * 0.03;
      flareMesh.scale.set(pulse, pulse, pulse);
      centerPointLight1.intensity = 8.5 + Math.sin(time * 2.0) * 2.0;

      // Orbital Rings Rotation
      orbitalGroup.rotation.y = time * 0.18;
      orbitalGroup.rotation.x = Math.sin(time * 0.15) * 0.08;

      // Orbiting Node Beads
      orbitalNodes.forEach((node) => {
        node.angle += node.speed;
        node.mesh.position.x = Math.cos(node.angle) * node.ringRadius;
        node.mesh.position.y = Math.sin(node.angle) * node.ringRadius;
      });

      // Subtle ambient particle drift
      particles.rotation.y = time * 0.08;
      particles.rotation.x = time * 0.04;

      // Gentle floating levitation
      orbGroup.position.y = Math.sin(time * 1.1) * 0.05;

      // Smooth mouse parallax damping
      orbGroup.rotation.y += (targetRotY - orbGroup.rotation.y) * 0.04;
      orbGroup.rotation.x += (targetRotX - orbGroup.rotation.x) * 0.04;

      renderer.render(scene, camera);
    };

    animate();

    // ═════════════════════════════════════════════
    //  CLEANUP
    // ═════════════════════════════════════════════
    return () => {
      resizeObserver.disconnect();
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("mousemove", onMouseMove);
      cancelAnimationFrame(frameRef.current);
      cubeRenderTarget.dispose();
      renderer.dispose();
      scene.traverse((obj) => {
        if (obj instanceof THREE.Mesh || obj instanceof THREE.Points) {
          obj.geometry.dispose();
          if (Array.isArray(obj.material)) {
            obj.material.forEach((m) => m.dispose());
          } else {
            obj.material.dispose();
          }
        }
      });
    };
  }, [speed]);

  return (
    <div
      ref={containerRef}
      className={`relative flex items-center justify-center select-none ${className}`}
    >
      {/* 
        Restrained Cyberpunk Ambient Glow:
        Transition: black → deep purple → violet → black
        Zero milky wash; pure dark contrast.
      */}
      <div className="absolute w-[80%] h-[80%] rounded-full bg-[radial-gradient(ellipse_at_center,rgba(109,40,217,0.22)_0%,rgba(17,16,74,0.12)_45%,transparent_70%)] blur-[45px] pointer-events-none" />
      <div className="absolute w-[60%] h-[60%] rounded-full bg-[radial-gradient(ellipse_at_center,rgba(0,217,255,0.14)_0%,transparent_65%)] blur-[35px] pointer-events-none translate-x-6 -translate-y-4" />

      {/* Ground bounce light reflection beneath the sphere (matching reference image) */}
      <div className="absolute bottom-2 sm:bottom-4 w-[55%] h-5 rounded-full bg-[radial-gradient(ellipse_at_center,rgba(139,92,246,0.32)_0%,rgba(109,40,217,0.1)_50%,transparent_75%)] blur-[18px] pointer-events-none" />

      {/* Transparent WebGL Canvas — 100% sharp 3D cyber-AI neural core */}
      <canvas
        ref={canvasRef}
        className="w-full h-full block"
        style={{ background: "transparent" }}
      />
    </div>
  );
}
