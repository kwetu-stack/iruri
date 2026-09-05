document.querySelectorAll('[data-counter]').forEach((counter) => {
    const target = Number(counter.dataset.counter);
    let value = 0;
    const step = Math.max(1, Math.ceil(target / 45));
    const tick = () => {
        value = Math.min(target, value + step);
        counter.textContent = value.toLocaleString();
        if (value < target) window.requestAnimationFrame(tick);
    };
    tick();
});
