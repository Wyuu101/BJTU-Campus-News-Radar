const csrfToken = () => {
  const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
};

const api = async (url, options = {}) => {
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken(),
      ...(options.headers || {}),
    },
  });
  const data = await response.json();
  if (!response.ok || data.ok === false) {
    const error = new Error(data.message || "请求没有成功，请稍后再试。");
    error.data = data;
    error.status = response.status;
    throw error;
  }
  return data;
};

const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (char) => ({
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  "\"": "&quot;",
  "'": "&#39;",
}[char]));

const PREVIEW_SLIDES = [
  {
    image: "/static/notice_app/concept_images/concept_img1.png",
    alt: "轮播图1",
    caption: "汇总校园各类讯息的链接索引，通过邮件及时提醒您前往官网查看。",
  },
  {
    image: "/static/notice_app/concept_images/concept_img2.png",
    alt: "轮播图2",
    caption: "提醒邮件内部页面展示，点击按钮即可跳转至信息源查看。",
  },
  {
    image: "/static/notice_app/concept_images/concept_img3.png",
    alt: "轮播图3",
    caption: "您可根据个人喜好开启或关闭接收指定部分的新讯通知。",
  },
];

let registrationUserLimit = 300;
let registrationClosed = false;

const capacityNoteText = () => (
  `由于个人财力有限，无法承担购买更多邮件通知服务的费用，本服务将在总用户数达${registrationUserLimit}人后关闭添加邮箱功能。为尽可能服务更多同学，建议大家每人只添加一个常用邮箱即可。`
);

const modal = {
  el: document.getElementById("modal"),
  title: document.getElementById("modalTitle"),
  message: document.getElementById("modalMessage"),
  confirm: document.querySelector(".modal-confirm"),
  close: document.querySelector(".modal-close"),
  onConfirm: null,
  show(title, message, onConfirm = null) {
    this.title.textContent = title;
    this.message.textContent = message;
    this.onConfirm = onConfirm;
    this.el.hidden = false;
  },
  hide() {
    this.el.hidden = true;
    this.onConfirm = null;
  },
};

if (modal.el) {
  modal.confirm.addEventListener("click", () => {
    const callback = modal.onConfirm;
    modal.hide();
    if (callback) callback();
  });
  modal.close.addEventListener("click", () => modal.hide());
}

const drawChart = (points) => {
  const svg = document.getElementById("trendChart");
  if (!svg) return;
  const width = 720;
  const height = 260;
  const padding = 34;
  const max = Math.max(1, ...points.map((point) => point.count));
  const coords = points.map((point, index) => {
    const x = padding + (index * (width - padding * 2)) / Math.max(1, points.length - 1);
    const y = height - padding - (point.count / max) * (height - padding * 2);
    return { ...point, x, y };
  });
  const path = coords.map((point, index) => {
    if (index === 0) return `M ${point.x} ${point.y}`;
    const previous = coords[index - 1];
    const cx = (previous.x + point.x) / 2;
    return `C ${cx} ${previous.y}, ${cx} ${point.y}, ${point.x} ${point.y}`;
  }).join(" ");

  svg.innerHTML = `
    <defs>
      <linearGradient id="lineGradient" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="#9f6f45"/>
        <stop offset="100%" stop-color="#4f9d73"/>
      </linearGradient>
    </defs>
    <path d="M ${padding} ${height - padding} H ${width - padding}" stroke="#dfd0c1" stroke-width="2" fill="none"/>
    <path d="${path}" stroke="url(#lineGradient)" stroke-width="5" stroke-linecap="round" fill="none"/>
    ${coords.map((point) => `<text class="chart-value-label" x="${point.x}" y="${Math.max(18, point.y - 14)}" text-anchor="middle">${point.count}</text>`).join("")}
    ${coords.map((point) => `<circle class="chart-point" cx="${point.x}" cy="${point.y}" r="5" fill="#fffaf5" stroke="#7c4f2c" stroke-width="3"><title>${point.date}: ${point.count}</title></circle>`).join("")}
    ${coords.map((point, index) => `<text x="${point.x}" y="${height - 8}" text-anchor="${index === 0 ? "start" : index === coords.length - 1 ? "end" : "middle"}" fill="#8a7a6b" font-size="12">${point.date.slice(5)}</text>`).join("")}
  `;
};

const initLogin = async () => {
  const form = document.getElementById("loginForm");
  if (!form) return;
  const captchaButton = document.getElementById("captchaButton");
  const captchaImage = document.getElementById("captchaImage");
  const captchaRateTip = document.getElementById("captchaRateTip");
  const sendCodeButton = document.getElementById("sendCodeButton");
  const emailInput = document.getElementById("emailInput");
  const captchaInput = document.getElementById("captchaInput");
  const codeInput = document.getElementById("codeInput");
  const privacyConsentInput = document.getElementById("privacyConsentInput");
  let cooldownTimer = null;
  let captchaKey = "";
  let captchaTipTimer = null;

  const applyCaptcha = (captcha) => {
    captchaKey = captcha.key;
    captchaImage.src = captcha.imageUrl;
    captchaInput.value = "";
  };

  const showCaptchaRateTip = (message) => {
    captchaRateTip.textContent = message;
    captchaRateTip.classList.add("visible");
    clearTimeout(captchaTipTimer);
    captchaTipTimer = setTimeout(() => {
      captchaRateTip.classList.remove("visible");
    }, 1800);
  };

  const refreshCaptcha = async () => {
    try {
      const data = await api("/api/captcha/", { method: "GET" });
      applyCaptcha(data.captcha);
    } catch (error) {
      showCaptchaRateTip(error.message || "操作太快，请稍后再换一张。");
    }
  };

  const startCooldown = (seconds) => {
    let remaining = seconds;
    sendCodeButton.disabled = true;
    sendCodeButton.textContent = `${remaining}s`;
    clearInterval(cooldownTimer);
    cooldownTimer = setInterval(() => {
      remaining -= 1;
      if (remaining <= 0) {
        clearInterval(cooldownTimer);
        sendCodeButton.disabled = false;
        sendCodeButton.textContent = "发送";
      } else {
        sendCodeButton.textContent = `${remaining}s`;
      }
    }, 1000);
  };

  captchaButton.addEventListener("click", refreshCaptcha);
  sendCodeButton.addEventListener("click", async () => {
    try {
      const data = await api("/api/request-code/", {
        method: "POST",
        body: JSON.stringify({
          email: emailInput.value,
          captcha: captchaInput.value,
          captchaKey,
        }),
      });
      startCooldown(data.cooldown || 60);
      modal.show("已发送", data.message);
    } catch (error) {
      if (error.data && error.data.captcha) {
        applyCaptcha(error.data.captcha);
      }
      modal.show("再看一眼", error.message);
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (privacyConsentInput && !privacyConsentInput.checked) {
      modal.show("请先确认", "请阅读《隐私条款》内容，勾选后以同意使用本服务");
      return;
    }
    try {
      const data = await api("/api/login/", {
        method: "POST",
        body: JSON.stringify({ email: emailInput.value, code: codeInput.value }),
      });
      window.location.href = data.redirect;
    } catch (error) {
      modal.show("验证失败", error.message);
    }
  });

  refreshCaptcha();
};

const initStats = async () => {
  try {
    const data = await api("/api/public-stats/", { method: "GET" });
    registrationUserLimit = Number(data.registrationUserLimit || registrationUserLimit);
    registrationClosed = Boolean(data.registrationClosed);
    drawChart(data.points || []);
    const userCount = document.getElementById("currentUserCount");
    if (userCount) userCount.textContent = data.currentUserCount || 0;
    const capacityNote = document.getElementById("capacityNote");
    if (capacityNote) {
      capacityNote.textContent = capacityNoteText();
      capacityNote.classList.toggle("is-closed", registrationClosed);
    }
  } catch {
    drawChart(Array.from({ length: 10 }, (_, index) => ({ date: `--${index + 1}`, count: 0 })));
  }
};

const initPreviewCarousel = () => {
  const track = document.getElementById("previewTrack");
  const caption = document.getElementById("previewCaption");
  const dots = document.getElementById("previewDots");
  const prevButton = document.getElementById("previewPrev");
  const nextButton = document.getElementById("previewNext");
  if (!track || !caption || !dots || !prevButton || !nextButton) return;

  let currentIndex = 0;
  let timer = null;
  const slides = PREVIEW_SLIDES.length > 0 ? PREVIEW_SLIDES : [{
    image: "",
    alt: "效果预览",
    caption: "这里预留效果图说明文字。",
  }];

  track.innerHTML = slides.map((slide, index) => {
    const image = String(slide.image || "").trim();
    const alt = escapeHtml(slide.alt || `效果图 ${index + 1}`);
    if (!image) {
      return `
        <div class="preview-slide">
          <div class="preview-placeholder">${alt}</div>
        </div>
      `;
    }
    return `
      <div class="preview-slide">
        <img src="${escapeHtml(image)}" alt="${alt}">
      </div>
    `;
  }).join("");

  dots.innerHTML = slides.map((_slide, index) => (
    `<button type="button" class="preview-dot" aria-label="第 ${index + 1} 张"></button>`
  )).join("");

  const dotButtons = [...dots.querySelectorAll(".preview-dot")];
  const render = () => {
    track.style.transform = `translateX(-${currentIndex * 100}%)`;
    caption.textContent = slides[currentIndex].caption || "";
    dotButtons.forEach((dot, index) => {
      dot.classList.toggle("active", index === currentIndex);
    });
  };
  const goTo = (index) => {
    currentIndex = (index + slides.length) % slides.length;
    render();
  };
  const restart = () => {
    clearInterval(timer);
    timer = setInterval(() => goTo(currentIndex + 1), 5000);
  };

  prevButton.addEventListener("click", () => {
    goTo(currentIndex - 1);
    restart();
  });
  nextButton.addEventListener("click", () => {
    goTo(currentIndex + 1);
    restart();
  });
  dotButtons.forEach((dot, index) => {
    dot.addEventListener("click", () => {
      goTo(index);
      restart();
    });
  });

  render();
  restart();
};

const initSettings = async () => {
  const grid = document.getElementById("sectionGrid");
  if (!grid) return;
  const userEmail = document.getElementById("userEmail");
  const deliveryHint = document.getElementById("deliveryHint");
  const saveButton = document.getElementById("savePreferencesButton");
  const deleteButton = document.getElementById("deleteAccountButton");

  const [me, sectionsData] = await Promise.all([
    api("/api/me/", { method: "GET" }),
    api("/api/sections/", { method: "GET" }),
  ]);
  userEmail.textContent = me.email;
  if (deliveryHint) {
    deliveryHint.textContent = `如果有校园新事发现，将会在当天的${me.dailyNotificationDisplayTime || "18:30"}左右为您整合消息索引并发送到您的邮箱。`;
  }
  const selected = new Set(me.preferences || []);

  grid.innerHTML = (sectionsData.sections || []).map((section) => {
    const checked = selected.size === 0 || selected.has(section);
    const safeSection = escapeHtml(section);
    return `
      <label class="section-card ${checked ? "active" : ""}">
        <input type="checkbox" value="${safeSection}" ${checked ? "checked" : ""}>
        <span>${safeSection}</span>
      </label>
    `;
  }).join("");

  grid.addEventListener("change", (event) => {
    const input = event.target;
    if (input.matches("input[type='checkbox']")) {
      input.closest(".section-card").classList.toggle("active", input.checked);
    }
  });

  saveButton.addEventListener("click", async () => {
    const sections = [...grid.querySelectorAll("input[type='checkbox']:checked")].map((input) => input.value);
    try {
      const data = await api("/api/preferences/", {
        method: "POST",
        body: JSON.stringify({ sections }),
      });
      modal.show("已保存", data.message);
    } catch (error) {
      modal.show("保存失败", error.message);
    }
  });

  deleteButton.addEventListener("click", () => {
    modal.show("确认注销吗", "该邮箱将停止接收新消息提醒", async () => {
      try {
        const data = await api("/api/account/", { method: "DELETE" });
        window.location.href = data.redirect;
      } catch (error) {
        modal.show("注销失败", error.message);
      }
    });
  });
};

const initUnsubscribe = () => {
  const modalEl = document.getElementById("unsubscribeModal");
  if (!modalEl) return;
  const confirmButton = document.getElementById("unsubscribeConfirm");
  const cancelButton = document.getElementById("unsubscribeCancel");
  const closeButton = document.getElementById("unsubscribeClose");
  const successPanel = document.getElementById("unsubscribeSuccess");
  const title = document.getElementById("unsubscribeTitle");
  const message = document.getElementById("unsubscribeMessage");
  const token = window.UNSUBSCRIBE_TOKEN || "";

  const closeToHome = () => {
    window.location.href = "/";
  };

  const showSuccess = () => {
    modalEl.hidden = true;
    successPanel.hidden = false;
  };

  const showError = (text) => {
    title.textContent = "退订失败";
    message.textContent = text;
    confirmButton.hidden = true;
    cancelButton.textContent = "返回首页";
  };

  confirmButton.addEventListener("click", async () => {
    try {
      await api("/api/unsubscribe/", {
        method: "POST",
        body: JSON.stringify({ token }),
      });
      showSuccess();
    } catch (error) {
      showError(error.message);
    }
  });
  cancelButton.addEventListener("click", closeToHome);
  closeButton.addEventListener("click", closeToHome);
};

initStats();
initPreviewCarousel();
initLogin();
initUnsubscribe();
initSettings().catch((error) => modal.show("加载失败", error.message));
