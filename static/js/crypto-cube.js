// CYBER SHATS — Qo'shimcha 3D elementlar (Three.js r128 asosida)
// Aylanuvchi "shifrlash kub"i — ma'lumotlar/xavfsizlik mavzusidagi sahifalar uchun.

/**
 * Aylanuvchi wireframe kub — Hacker Lab, pricing kabi sahifalar uchun.
 * Kichik konteynerda ishlaydi.
 */
function csCreateCryptoCube(containerId, opts) {
    opts = opts || {};
    const container = document.getElementById(containerId);
    if (!container || typeof THREE === 'undefined') return null;

    const isRedTheme = opts.theme === 'vip' || document.body.classList.contains('vip-theme');
    const mainColor = isRedTheme ? 0xff3030 : 0x00ff41;
    const accentColor = isRedTheme ? 0xff6b6b : 0x00ccff;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(60, container.clientWidth / container.clientHeight, 0.1, 100);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);

    const group = new THREE.Group();

    // Asosiy kub (yarim shaffof)
    const boxGeo = new THREE.BoxGeometry(1.6, 1.6, 1.6);
    const boxMat = new THREE.MeshPhongMaterial({
        color: 0x050505, emissive: mainColor, emissiveIntensity: 0.08,
        transparent: true, opacity: 0.55
    });
    const box = new THREE.Mesh(boxGeo, boxMat);
    group.add(box);

    // Wireframe qirralar
    const edges = new THREE.EdgesGeometry(boxGeo);
    const lineMat = new THREE.LineBasicMaterial({ color: mainColor, transparent: true, opacity: 0.9 });
    const wireframe = new THREE.LineSegments(edges, lineMat);
    group.add(wireframe);

    // Ichki kichik kub (qarama-qarshi aylanish)
    const innerGeo = new THREE.BoxGeometry(0.8, 0.8, 0.8);
    const innerEdges = new THREE.EdgesGeometry(innerGeo);
    const innerMat = new THREE.LineBasicMaterial({ color: accentColor, transparent: true, opacity: 0.7 });
    const innerWire = new THREE.LineSegments(innerEdges, innerMat);
    group.add(innerWire);

    scene.add(group);

    const ambientLight = new THREE.AmbientLight(0x111111, 0.8);
    scene.add(ambientLight);
    const pointLight = new THREE.PointLight(mainColor, 1.0, 50);
    pointLight.position.set(3, 3, 3);
    scene.add(pointLight);

    camera.position.z = opts.cameraZ || 4;

    function onResize() {
        if (!container.clientWidth) return;
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    }
    window.addEventListener('resize', onResize);

    let running = true;
    function animate() {
        if (!running) return;
        requestAnimationFrame(animate);
        group.rotation.y += 0.006;
        group.rotation.x += 0.003;
        innerWire.rotation.y -= 0.012;
        innerWire.rotation.x -= 0.008;
        renderer.render(scene, camera);
    }
    animate();

    return {
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

/**
 * Auto-init: data-crypto-cube atributi bo'lgan barcha elementlarda
 * avtomatik ishga tushadi. data-theme="vip" bo'lsa qizil rangda chiziladi
 * (foydalanuvchining shaxsiy temasidan qat'iy nazar — masalan pricing
 * sahifasida SHATS CYBER PRO reklama kartochkasi har doim qizil bo'lsin uchun).
 */
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-crypto-cube]').forEach(function (el) {
        var theme = el.getAttribute('data-theme') || null;
        csCreateCryptoCube(el.id, { cameraZ: 4, theme: theme });
    });
});
