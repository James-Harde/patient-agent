/* 作者：小红书@人间清醒的李某人 */

const queryForm = document.getElementById("queryForm");
const queryInput = document.getElementById("queryInput");
const imageInput = document.getElementById("imageInput");
const imagePreview = document.getElementById("imagePreview");
const speechVoiceSelect = document.getElementById("speechVoiceSelect");
const submitButton = document.getElementById("submitButton");
const statusBadge = document.getElementById("statusBadge");
const answerOutput = document.getElementById("answerOutput");
const audioVoiceMeta = document.getElementById("audioVoiceMeta");
const audioPlayer = document.getElementById("audioPlayer");

const VOICE_LABELS = {
  longanyang: "龙安洋 · 阳光大男孩",
  longanhuan: "龙安欢 · 欢脱元气女",
  longxiaochun_v3: "龙小淳 · 知性积极女",
  longxiaoxia_v3: "龙小夏 · 沉稳权威女",
  longyumi_v3: "YUMI · 正经青年女",
  longanwen_v3: "龙安温 · 优雅知性女",
  longanli_v3: "龙安莉 · 利落从容女",
  longanyun_v3: "龙安昀 · 居家暖男",
};

function isSpeechEnabled() {
  return speechVoiceSelect.value !== "none";
}

function setStatus(text, variant = "") {
  statusBadge.textContent = text;
  statusBadge.className = `status-badge${variant ? ` ${variant}` : ""}`;
}

function setBlockContent(element, content, placeholder = false) {
  element.textContent = content;
  element.classList.toggle("placeholder", placeholder);
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = typeof reader.result === "string" ? reader.result : "";
      const [, base64 = ""] = result.split(",");
      resolve(base64);
    };
    reader.onerror = () => reject(new Error("图片读取失败"));
    reader.readAsDataURL(file);
  });
}

function renderImagePreview(file) {
  if (!file) {
    imagePreview.classList.add("is-empty");
    imagePreview.innerHTML = "<span>未选择图片</span>";
    return;
  }

  const previewUrl = URL.createObjectURL(file);
  imagePreview.classList.remove("is-empty");
  imagePreview.innerHTML = `<img src="${previewUrl}" alt="预览图片" />`;
}

async function buildPayload() {
  const payload = {
    query: queryInput.value.trim(),
    images: [],
    debug_planner: false,
    enable_speech: isSpeechEnabled(),
    speech_voice: isSpeechEnabled() ? speechVoiceSelect.value : "longanyang",
    speech_format: "mp3",
  };

  const file = imageInput.files[0];
  if (file) {
    const imageBase64 = await fileToBase64(file);
    payload.images.push({
      image_base64: imageBase64,
      mime_type: file.type || "image/png",
    });
  }

  return payload;
}

async function submitQuery(event) {
  event.preventDefault();

  if (!queryInput.value.trim()) {
    setStatus("请输入问题", "error");
    return;
  }

  submitButton.disabled = true;
  setStatus("查询中", "loading");
  setBlockContent(answerOutput, "正在调用 /api/agent/query ...");
  audioVoiceMeta.classList.add("hidden");
  audioVoiceMeta.textContent = "";
  audioPlayer.classList.add("hidden");
  audioPlayer.removeAttribute("src");

  try {
    const payload = await buildPayload();
    const response = await fetch("/api/agent/query", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "请求失败");
    }

    setBlockContent(answerOutput, data.answer || "接口未返回 answer。");

    if (data.speech_download_url) {
      const voiceCode = data.speech_voice || speechVoiceSelect.value;
      const voiceLabel = VOICE_LABELS[voiceCode] || voiceCode;
      audioVoiceMeta.textContent = `当前声音：${voiceLabel}`;
      audioVoiceMeta.classList.remove("hidden");
      audioPlayer.src = data.speech_download_url;
      audioPlayer.classList.remove("hidden");
    }

    setStatus("查询完成", "success");
  } catch (error) {
    const message = error instanceof Error ? error.message : "请求失败";
    setBlockContent(answerOutput, message);
    setStatus("查询失败", "error");
  } finally {
    submitButton.disabled = false;
  }
}

queryForm.addEventListener("submit", submitQuery);
imageInput.addEventListener("change", (event) => {
  const file = event.target.files[0];
  renderImagePreview(file);
});

document.querySelectorAll(".prompt-chip").forEach((button) => {
  button.addEventListener("click", () => {
    queryInput.value = button.dataset.prompt || "";
    queryInput.focus();
  });
});
