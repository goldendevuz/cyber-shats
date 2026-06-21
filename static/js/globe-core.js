// CYBER SHATS — Uch o'lchamli Yer shari (Three.js r128 asosida, umumiy modul)
// Barcha sahifalarda ishlatiladigan asosiy globe yaratish funksiyasi
function csCreateGlobe(containerId, opts) {
    opts = opts || {};
    const container = document.getElementById(containerId);
    if (!container || typeof THREE === 'undefined') return null;

    // Rang sxemasi: standart yashil, yoki opts.theme='vip' bo'lsa qizil
    // (SHATS CYBER PRO foydalanuvchilari uchun)
    const isRedTheme = opts.theme === 'vip' || document.body.classList.contains('vip-theme');
    const colors = isRedTheme
        ? { core: 0x1a0000, emissive: 0xff3030, wire: 0xff3030, dots: 0xff5e5e, ring: 0xff6b6b, ambient: 0x220000, point: 0xff3030 }
        : { core: 0x001a00, emissive: 0x00ff41, wire: 0x00ff41, dots: 0x00ff88, ring: 0x00ccff, ambient: 0x002200, point: 0x00ff41 };

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);

    // Yer shari asosi
    const geometry = new THREE.SphereGeometry(2, 48, 48);
    const material = new THREE.MeshPhongMaterial({
        color: colors.core,
        emissive: colors.emissive,
        emissiveIntensity: 0.06,
        wireframe: false,
        transparent: true,
        opacity: 0.85
    });
    const globe = new THREE.Mesh(geometry, material);
    scene.add(globe);

    // Wireframe ustma-ust
    const wireGeometry = new THREE.SphereGeometry(2.015, 28, 28);
    const wireMaterial = new THREE.MeshBasicMaterial({ color: colors.wire, wireframe: true, transparent: true, opacity: 0.18 });
    const wireGlobe = new THREE.Mesh(wireGeometry, wireMaterial);
    scene.add(wireGlobe);

    // Tarmoq nuqtalari (random "shaharlar")
    const dotsGeo = new THREE.BufferGeometry();
    const dotCount = 140;
    const positions = new Float32Array(dotCount * 3);
    for (let i = 0; i < dotCount; i++) {
        const phi = Math.acos(-1 + (2 * i) / dotCount);
        const theta = Math.sqrt(dotCount * Math.PI) * phi;
        const r = 2.02;
        positions[i * 3] = r * Math.cos(theta) * Math.sin(phi);
        positions[i * 3 + 1] = r * Math.sin(theta) * Math.sin(phi);
        positions[i * 3 + 2] = r * Math.cos(phi);
    }
    dotsGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const dotsMat = new THREE.PointsMaterial({ color: colors.dots, size: 0.035, transparent: true, opacity: 0.85 });
    const dots = new THREE.Points(dotsGeo, dotsMat);
    scene.add(dots);

    // Tashqi orbit halqa
    const ringGeo = new THREE.RingGeometry(2.6, 2.615, 80);
    const ringMat = new THREE.MeshBasicMaterial({ color: colors.ring, transparent: true, opacity: 0.25, side: THREE.DoubleSide });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    ring.rotation.x = Math.PI / 2.4;
    scene.add(ring);

    const ambientLight = new THREE.AmbientLight(colors.ambient, 0.7);
    scene.add(ambientLight);
    const pointLight = new THREE.PointLight(colors.point, 1.2, 100);
    pointLight.position.set(5, 5, 5);
    scene.add(pointLight);

    camera.position.z = opts.cameraZ || 5;

    function onResize() {
        if (!container.clientWidth) return;
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    }
    window.addEventListener('resize', onResize);

    let speed = opts.speed || 0.0028;
    let running = true;
    function animate() {
        if (!running) return;
        requestAnimationFrame(animate);
        globe.rotation.y += speed;
        wireGlobe.rotation.y += speed;
        dots.rotation.y += speed;
        ring.rotation.z += speed * 0.6;
        renderer.render(scene, camera);
    }
    animate();

    return {
        scene, camera, renderer, globe, wireGlobe, ring,
        setSpeed: (v) => { speed = v; },
        stop: () => { running = false; },
        destroy: () => {
            running = false;
            window.removeEventListener('resize', onResize);
            if (renderer.domElement && renderer.domElement.parentNode) {
                renderer.domElement.parentNode.removeChild(renderer.domElement);
            }
        }
    };
}
