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

document.querySelectorAll('[data-enquiry-source]').forEach((button) => {
    button.addEventListener('click', () => {
        const source = document.querySelector('#enquiry-source');
        if (source) source.value = button.dataset.enquirySource;
    });
});

document.querySelectorAll('[data-gallery-image]').forEach((button) => {
    button.addEventListener('click', () => {
        const image = document.querySelector('#gallery-main-image');
        if (!image) return;
        image.src = button.dataset.galleryImage;
        document.querySelectorAll('.gallery-thumb').forEach((thumb) => {
            thumb.classList.toggle('active', thumb === button);
        });
    });
});

document.querySelectorAll('[data-copy-link]').forEach((button) => {
    button.addEventListener('click', async () => {
        try {
            await navigator.clipboard.writeText(button.dataset.copyLink);
            const originalText = button.textContent;
            button.textContent = 'Link copied';
            window.setTimeout(() => { button.textContent = originalText; }, 1800);
        } catch (error) {
            window.prompt('Copy property link', button.dataset.copyLink);
        }
    });
});
