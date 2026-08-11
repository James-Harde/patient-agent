/* 作者：小红书@人间清醒的李某人 */

const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const chatImageInput = document.getElementById("chatImageInput");
const chatImagePreview = document.getElementById("chatImagePreview");
const chatSpeechVoiceSelect = document.getElementById("chatSpeechVoiceSelect");
const sendChatButton = document.getElementById("sendChatButton");
const clearChatButton = document.getElementById("clearChatButton");
const chatStatusBadge = document.getElementById("chatStatusBadge");
const chatTimeline = document.getElementById("chatTimeline");

const chatState = {
  messages: [],
};

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
  return chatSpeechVoiceSelect.value !== "none";
}

function setChatStatus(text, variant = "") {
  chatStatusBadge.textContent = text;
  chatStatusBadge.className = `status-badge${variant ? ` ${variant}` : ""}`;
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

function renderPreview(container, file, emptyText) {
  if (!file) {
    container.classList.add("is-empty");
    container.innerHTML = `<span>${emptyText}</span>`;
    return;
  }

  const previewUrl = URL.createObjectURL(file);
  container.classList.remove("is-empty");
  container.innerHTML = `<img src="${previewUrl}" alt="预览图片" />`;
}

function escapeHtml(text) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderChat() {
  if (chatState.messages.length === 0) {
    chatTimeline.innerHTML = `
      <div class="empty-chat-state">
        <h3>还没有消息</h3>
        <p>先输入一句话，页面会按聊天形式展示用户消息和助手回复。</p>
      </div>
    `;
    return;
  }

  chatTimeline.innerHTML = chatState.messages
    .map((message) => {
      const toolsBlock = message.toolOutputs
        ? `<details class="message-meta"><summary>工具调用</summary><pre>${escapeHtml(
            JSON.stringify(message.toolOutputs, null, 2)
          )}</pre></details>`
        : "";
      const imageBlock = message.imageUrl
        ? `<img class="message-image" src="${message.imageUrl}" alt="消息图片" />`
        : "";
      const audioBlock = message.audioUrl
        ? `<p class="audio-meta">当前声音：${escapeHtml(message.voiceLabel || message.voiceCode || "默认音色")}</p><audio controls class="message-audio" src="${message.audioUrl}"></audio>`
        : "";

      return `
        <article class="message-bubble ${message.role === "user" ? "user-bubble" : "assistant-bubble"}">
          <header>
            <span>${message.role === "user" ? "你" : "助手"}</span>
          </header>
          <p>${escapeHtml(message.content).replaceAll("\n", "<br />")}</p>
          ${imageBlock}
          ${audioBlock}
          ${toolsBlock}
        </article>
      `;
    })
    .join("");

  chatTimeline.scrollTop = chatTimeline.scrollHeight;
}

function buildContextualQuery(nextMessage) {
  const recentMessages = chatState.messages.slice(-6);
  if (recentMessages.length === 0) {
    return nextMessage;
  }

  const transcript = recentMessages
    .map((message) => `${message.role === "user" ? "用户" : "助手"}：${message.content}`)
    .join("\n");

  return `以下是最近对话上下文，请结合上下文回答最后一个问题。\n\n${transcript}\n用户：${nextMessage}`;
}

async function buildPayload() {
  const file = chatImageInput.files[0];
  const payload = {
    query: buildContextualQuery(chatInput.value.trim()),
    images: [],
    debug_planner: false,
    enable_speech: isSpeechEnabled(),
    speech_voice: isSpeechEnabled() ? chatSpeechVoiceSelect.value : "longanyang",
    speech_format: "mp3",
  };

  if (file) {
    const imageBase64 = await fileToBase64(file);
    payload.images.push({
      image_base64: imageBase64,
      mime_type: file.type || "image/png",
    });
  }

  return payload;
}

function addUserMessage(content, file) {
  chatState.messages.push({
    role: "user",
    content,
    imageUrl: file ? URL.createObjectURL(file) : "",
  });
  renderChat();
}

function addAssistantMessage(data) {
  chatState.messages.push({
    role: "assistant",
    content: data.answer || "接口未返回 answer。",
    toolOutputs: data.tool_outputs && data.tool_outputs.length > 0 ? data.tool_outputs : null,
    audioUrl: data.speech_download_url || "",
    voiceCode: data.speech_voice || chatSpeechVoiceSelect.value,
    voiceLabel: VOICE_LABELS[data.speech_voice || chatSpeechVoiceSelect.value] || (data.speech_voice || chatSpeechVoiceSelect.value),
  });
  renderChat();
}

async function onSubmit(event) {
  event.preventDefault();

  const text = chatInput.value.trim();
  if (!text) {
    setChatStatus("请输入消息", "error");
    return;
  }

  const imageFile = chatImageInput.files[0];
  addUserMessage(text, imageFile);
  sendChatButton.disabled = true;
  setChatStatus("回复中", "loading");

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

    addAssistantMessage(data);
    chatInput.value = "";
    chatImageInput.value = "";
    renderPreview(chatImagePreview, null, "本轮未选择图片");
    setChatStatus("已完成", "success");
  } catch (error) {
    const message = error instanceof Error ? error.message : "请求失败";
    chatState.messages.push({
      role: "assistant",
      content: `请求失败：${message}`,
    });
    renderChat();
    setChatStatus("请求失败", "error");
  } finally {
    sendChatButton.disabled = false;
  }
}

function clearChat() {
  chatState.messages = [];
  chatInput.value = "";
  chatImageInput.value = "";
  renderPreview(chatImagePreview, null, "本轮未选择图片");
  renderChat();
  setChatStatus("空闲");
}

chatForm.addEventListener("submit", onSubmit);
chatImageInput.addEventListener("change", (event) => {
  renderPreview(chatImagePreview, event.target.files[0], "本轮未选择图片");
});
clearChatButton.addEventListener("click", clearChat);

document.querySelectorAll(".prompt-chip").forEach((button) => {
  button.addEventListener("click", () => {
    chatInput.value = button.dataset.prompt || "";
    chatInput.focus();
  });
});

renderChat();
