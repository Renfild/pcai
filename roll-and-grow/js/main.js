(() => {
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;

  /* ---------- Loader ---------- */
  const loader = document.getElementById("loader");
  window.addEventListener("load", () => {
    requestAnimationFrame(() => {
      setTimeout(() => loader?.classList.add("is-done"), reducedMotion ? 0 : 550);
    });
  });
  /* Safety: never leave the loader stuck */
  setTimeout(() => loader?.classList.add("is-done"), 2200);

  /* ---------- Custom cursor ---------- */
  const cursor = document.getElementById("cursor");
  const cursorRing = document.getElementById("cursorRing");
  if (finePointer && cursor && cursorRing && !reducedMotion) {
    let mx = window.innerWidth / 2;
    let my = window.innerHeight / 2;
    let rx = mx;
    let ry = my;

    window.addEventListener("pointermove", (e) => {
      mx = e.clientX;
      my = e.clientY;
      cursor.style.transform = `translate(${mx}px, ${my}px) translate(-50%, -50%)`;
    });

    const tickCursor = () => {
      rx += (mx - rx) * 0.18;
      ry += (my - ry) * 0.18;
      cursorRing.style.transform = `translate(${rx}px, ${ry}px) translate(-50%, -50%)`;
      requestAnimationFrame(tickCursor);
    };
    tickCursor();

    const hoverables = "a, button, input, [data-magnetic]";
    document.querySelectorAll(hoverables).forEach((el) => {
      el.addEventListener("pointerenter", () => cursorRing.classList.add("is-hover"));
      el.addEventListener("pointerleave", () => cursorRing.classList.remove("is-hover"));
    });
  }

  /* ---------- Magnetic buttons ---------- */
  if (finePointer && !reducedMotion) {
    document.querySelectorAll("[data-magnetic]").forEach((el) => {
      el.addEventListener("pointermove", (e) => {
        const rect = el.getBoundingClientRect();
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;
        el.style.transform = `translate(${x * 0.22}px, ${y * 0.28}px)`;
      });
      el.addEventListener("pointerleave", () => {
        el.style.transform = "";
      });
    });
  }

  /* ---------- Nav scroll + mobile menu ---------- */
  const nav = document.getElementById("nav");
  const menuBtn = document.getElementById("menuBtn");
  const mobileNav = document.getElementById("mobileNav");

  const progress = document.getElementById("scrollProgress");
  const onScrollNav = () => {
    nav?.classList.toggle("is-scrolled", window.scrollY > 24);
    if (progress) {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      const pct = max > 0 ? (window.scrollY / max) * 100 : 0;
      progress.style.width = `${pct}%`;
    }
  };
  onScrollNav();
  window.addEventListener("scroll", onScrollNav, { passive: true });

  const closeMenu = () => {
    menuBtn?.setAttribute("aria-expanded", "false");
    mobileNav?.classList.remove("is-open");
    mobileNav?.setAttribute("hidden", "");
    document.body.classList.remove("menu-open");
  };

  menuBtn?.addEventListener("click", () => {
    const open = menuBtn.getAttribute("aria-expanded") === "true";
    if (open) {
      closeMenu();
    } else {
      menuBtn.setAttribute("aria-expanded", "true");
      mobileNav?.classList.add("is-open");
      mobileNav?.removeAttribute("hidden");
      document.body.classList.add("menu-open");
    }
  });

  mobileNav?.querySelectorAll("a").forEach((a) => a.addEventListener("click", closeMenu));

  /* ---------- Text split + reveal ---------- */
  document.querySelectorAll("[data-split]").forEach((el) => {
    const text = el.textContent.trim();
    el.textContent = "";
    [...text].forEach((ch, i) => {
      const span = document.createElement("span");
      span.className = "char";
      span.style.setProperty("--char-i", String(i));
      span.textContent = ch === " " ? "\u00A0" : ch;
      el.appendChild(span);
    });
  });

  const revealEls = document.querySelectorAll(".reveal, .step");
  if (reducedMotion) {
    revealEls.forEach((el) => el.classList.add("is-in"));
  } else if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-in");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.18, rootMargin: "0px 0px -8% 0px" }
    );
    revealEls.forEach((el) => io.observe(el));
  } else {
    revealEls.forEach((el) => el.classList.add("is-in"));
  }

  /* Kick hero brand in after loader — keep text readable if timing slips */
  const brand = document.querySelector(".hero__brand");
  const revealBrand = () => {
    if (!brand) return;
    brand.classList.add("is-ready");
    requestAnimationFrame(() => brand.classList.add("is-in"));
    setTimeout(() => {
      brand.querySelectorAll(".char").forEach((ch) => {
        ch.style.opacity = "1";
        ch.style.transform = "none";
      });
    }, 1600);
  };
  setTimeout(revealBrand, reducedMotion ? 0 : 780);

  /* ---------- Particles ---------- */
  const canvas = document.getElementById("particles");
  if (canvas && !reducedMotion) {
    const ctx = canvas.getContext("2d");
    let w = 0;
    let h = 0;
    let particles = [];
    let raf = 0;

    const resize = () => {
      const rect = canvas.parentElement.getBoundingClientRect();
      w = canvas.width = Math.floor(rect.width * devicePixelRatio);
      h = canvas.height = Math.floor(rect.height * devicePixelRatio);
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;
      ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
      spawn();
    };

    const spawn = () => {
      const count = Math.min(48, Math.floor((w * h) / (14000 * devicePixelRatio * devicePixelRatio)));
      particles = Array.from({ length: count }, () => ({
        x: Math.random() * (w / devicePixelRatio),
        y: Math.random() * (h / devicePixelRatio),
        r: 1 + Math.random() * 2.4,
        vx: -0.25 + Math.random() * 0.5,
        vy: -0.4 - Math.random() * 0.7,
        a: 0.2 + Math.random() * 0.55,
        hue: Math.random() > 0.65 ? "255,176,32" : "184,255,60",
      }));
    };

    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      particles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;
        if (p.y < -10) {
          p.y = h / devicePixelRatio + 10;
          p.x = Math.random() * (w / devicePixelRatio);
        }
        if (p.x < -10) p.x = w / devicePixelRatio + 10;
        if (p.x > w / devicePixelRatio + 10) p.x = -10;
        ctx.beginPath();
        ctx.fillStyle = `rgba(${p.hue},${p.a})`;
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
      });
      raf = requestAnimationFrame(draw);
    };

    resize();
    draw();
    window.addEventListener("resize", resize);
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) cancelAnimationFrame(raf);
      else draw();
    });
  }

  /* ---------- Hero orb parallax ---------- */
  const heroOrb = document.getElementById("heroOrb");
  if (heroOrb && finePointer && !reducedMotion) {
    const hero = document.querySelector(".hero");
    hero?.addEventListener("pointermove", (e) => {
      const rect = hero.getBoundingClientRect();
      const px = (e.clientX - rect.left) / rect.width - 0.5;
      const py = (e.clientY - rect.top) / rect.height - 0.5;
      heroOrb.style.translate = `${px * 36}px ${py * 24}px`;
    });
    hero?.addEventListener("pointerleave", () => {
      heroOrb.style.translate = "";
    });
  }

  /* ---------- Feature interactions ---------- */
  const dice = document.getElementById("dice");
  const growFill = document.getElementById("growFill");
  const growLabel = document.getElementById("growLabel");
  let growLevel = 1;

  const bumpGrow = () => {
    growLevel = growLevel >= 50 ? 1 : growLevel + Math.ceil(Math.random() * 7);
    if (growFill) growFill.style.width = `${Math.min(100, 10 + growLevel * 1.7)}%`;
    if (growLabel) growLabel.textContent = `${growLevel}x`;
  };

  if (!reducedMotion) {
    setInterval(() => {
      if (dice) {
        const n = 1 + Math.floor(Math.random() * 6);
        dice.querySelector(".dice__face").textContent = String(n);
      }
      bumpGrow();
    }, 2200);
  }

  /* ---------- Size playground ---------- */
  const slider = document.getElementById("sizeSlider");
  const sizeValue = document.getElementById("sizeValue");
  const sizeOrb = document.getElementById("sizeOrb");

  const applySize = (value) => {
    const v = Number(value);
    if (sizeValue) sizeValue.textContent = String(v);
    if (sizeOrb) {
      const scale = 0.25 + (v / 100) * 2.4;
      sizeOrb.style.setProperty("--s", scale.toFixed(3));
    }
  };

  if (slider) {
    applySize(slider.value);
    slider.addEventListener("input", (e) => applySize(e.target.value));

    if (!reducedMotion) {
      let auto = true;
      let dir = 1;
      slider.addEventListener("pointerdown", () => {
        auto = false;
      });
      setInterval(() => {
        if (!auto) return;
        let next = Number(slider.value) + dir * 1.5;
        if (next >= 100 || next <= 1) dir *= -1;
        next = Math.max(1, Math.min(100, next));
        slider.value = String(next);
        applySize(next);
      }, 50);
    }
  }
})();
