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

const COMPLETED_EXECUTION_LABELS = {
  "理解并规划问题": "已完成问题理解与规划",
  "验证患者身份": "已完成患者身份验证",
  "查询患者资料": "已完成患者资料查询",
  "查询病例信息": "已完成病例信息查询",
  "查询就诊记录": "已完成就诊记录查询",
  "调用业务工具": "已完成业务工具调用",
  "生成最终回答": "已完成最终回答生成",
};

const FAILED_EXECUTION_LABELS = {
  "理解并规划问题": "问题理解与规划失败",
  "验证患者身份": "患者身份验证失败",
  "查询患者资料": "患者资料查询失败",
  "查询病例信息": "病例信息查询失败",
  "查询就诊记录": "就诊记录查询失败",
  "调用业务工具": "业务工具调用失败",
  "生成最终回答": "最终回答生成失败",
};

const SAFE_TOOL_DISPLAY_NAMES = new Set([
  "验证患者身份",
  "查询患者资料",
  "查询病例信息",
  "查询就诊记录",
  "调用业务工具",
]);

/* ------------------------------------------------------------------ */
/*  Timer management — per-message elapsed-time counters              */
/* ------------------------------------------------------------------ */

const _activeTimers = new Map();
let _requestGeneration = 0;
let _activeRequest = null;

function _clearMessageTimer(message) {
  const existing = _activeTimers.get(message);
  if (existing != null) {
    clearInterval(existing);
    _activeTimers.delete(message);
  }
}

function _clearAllTimers() {
  for (const timerId of _activeTimers.values()) {
    clearInterval(timerId);
  }
  _activeTimers.clear();
}

function _startElapsedTimer(message, messageIndex) {
  _clearMessageTimer(message);
  const timerId = setInterval(() => {
    const msg = chatState.messages[messageIndex];
    if (msg !== message || message.executionState !== "running") {
      _clearMessageTimer(message);
      return;
    }
    renderChat();
  }, 1000);
  _activeTimers.set(message, timerId);
}

function _isCurrentRequest(requestId) {
  return _activeRequest?.requestId === requestId;
}

function _invalidateActiveRequest() {
  _requestGeneration += 1;
  const activeRequest = _activeRequest;
  _activeRequest = null;
  if (activeRequest) {
    activeRequest.controller.abort();
  }
}

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

function executionStepText(step) {
  if (step.status === "completed") {
    let text = COMPLETED_EXECUTION_LABELS[step.name] || `已完成${step.name}`;
    if (step._duration != null) {
      text += ` · ${step._duration} 秒`;
    }
    return text;
  }
  if (step.status === "failed") {
    let text = FAILED_EXECUTION_LABELS[step.name] || `${step.name}失败`;
    if (step._duration != null) {
      text += ` · ${step._duration} 秒`;
    }
    return text;
  }
  let text = `正在${step.name}`;
  if (step._startedAt) {
    const elapsed = Math.floor((Date.now() - step._startedAt) / 1000);
    text += ` · ${elapsed} 秒`;
  }
  return text;
}

function executionSummary(message) {
  const stepCount = message.executionSteps.length;
  if (message.executionState === "completed") {
    return `执行完成，共 ${stepCount} 个步骤`;
  }
  if (message.executionState === "failed") {
    return "执行失败";
  }
  return stepCount > 0 ? `执行中，共 ${stepCount} 个步骤` : "执行中";
}

function renderExecutionProcess(message, messageIndex) {
  if (message.role !== "assistant" || !message.executionSteps) {
    return "";
  }
  const steps = message.executionSteps
    .map(
      (step) => {
        const subtextHtml = step._subtext && step.status === "in-progress"
          ? `<span class="execution-step-subtext">${escapeHtml(step._subtext)}</span>`
          : "";
        return `
        <li class="execution-step ${step.status}">
          <span class="execution-step-marker" aria-hidden="true"></span>
          <span class="execution-step-body">
            <span>${escapeHtml(executionStepText(step))}</span>
            ${subtextHtml}
          </span>
        </li>
      `;
      }
    )
    .join("");
  return `
    <details class="message-meta execution-process" data-message-index="${messageIndex}"${message.executionOpen ? " open" : ""}>
      <summary>${escapeHtml(executionSummary(message))}</summary>
      <ol class="execution-step-list">${steps}</ol>
    </details>
  `;
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
    .map((message, messageIndex) => {
      const executionBlock = renderExecutionProcess(message, messageIndex);
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
          ${executionBlock}
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
    audioUrl: data.speech_download_url || "",
    voiceCode: data.speech_voice || chatSpeechVoiceSelect.value,
    voiceLabel: VOICE_LABELS[data.speech_voice || chatSpeechVoiceSelect.value] || (data.speech_voice || chatSpeechVoiceSelect.value),
  });
  renderChat();
}

function startStreamingAssistantMessage() {
  const message = {
    role: "assistant",
    content: "",
    audioUrl: "",
    voiceCode: "",
    voiceLabel: "",
    executionSteps: [],
    executionState: "running",
    executionOpen: true,
  };
  chatState.messages.push(message);
  renderChat();
  return message;
}

function applyStreamingDone(message, data) {
  _clearMessageTimer(message);
  message.content = data.answer || message.content || "接口未返回 answer。";
  message.audioUrl = data.speech_download_url || "";
  message.voiceCode = data.speech_voice || chatSpeechVoiceSelect.value;
  message.voiceLabel = VOICE_LABELS[message.voiceCode] || message.voiceCode;
  message.executionSteps.forEach((step) => {
    if (step.status === "in-progress") {
      step.status = "completed";
      if (step._startedAt) {
        step._duration = Math.floor((Date.now() - step._startedAt) / 1000);
      }
    }
  });
  message.executionState = "completed";
  message.executionOpen = false;
  renderChat();
}

function completeCurrentExecutionStep(message) {
  const currentStep = [...message.executionSteps]
    .reverse()
    .find((step) => step.status === "in-progress");
  if (currentStep) {
    currentStep.status = "completed";
    if (currentStep._startedAt) {
      currentStep._duration = Math.floor((Date.now() - currentStep._startedAt) / 1000);
    }
  }
}

function updateExecutionProcess(message, status) {
  message.executionOpen = true;
  const messageIndex = chatState.messages.indexOf(message);
  if (status.stage === "planning") {
    const planningStep = message.executionSteps.find(
      (step) => step.name === "理解并规划问题"
    );
    if (!planningStep) {
      _clearMessageTimer(message);
      message.executionSteps.push({
        name: "理解并规划问题",
        status: "in-progress",
        _startedAt: Date.now(),
        _subtext: "模型正在判断需要调用哪些业务能力",
      });
      _startElapsedTimer(message, messageIndex);
    }
  } else if (status.stage === "tool") {
    const safeName = SAFE_TOOL_DISPLAY_NAMES.has(status.name)
      ? status.name
      : "调用业务工具";
    if (status.status === "started") {
      completeCurrentExecutionStep(message);
      _clearMessageTimer(message);
      message.executionSteps.push({
        name: safeName,
        status: "in-progress",
        _startedAt: Date.now(),
      });
      _startElapsedTimer(message, messageIndex);
    } else {
      const toolStep = [...message.executionSteps]
        .reverse()
        .find((step) => step.name === safeName && step.status === "in-progress");
      if (toolStep) {
        toolStep.status = status.status === "failed" ? "failed" : "completed";
        if (toolStep._startedAt) {
          toolStep._duration = Math.floor((Date.now() - toolStep._startedAt) / 1000);
        }
        _clearMessageTimer(message);
      }
      if (status.status === "failed") {
        message.executionState = "failed";
      }
    }
  } else if (status.stage === "generating") {
    completeCurrentExecutionStep(message);
    _clearMessageTimer(message);
    message.executionSteps.push({
      name: "生成最终回答",
      status: "in-progress",
      _startedAt: Date.now(),
    });
    _startElapsedTimer(message, messageIndex);
  }
  renderChat();
}

function markExecutionFailed(message) {
  _clearMessageTimer(message);
  const currentStep = [...message.executionSteps]
    .reverse()
    .find((step) => step.status === "in-progress");
  if (currentStep) {
    currentStep.status = "failed";
    if (currentStep._startedAt) {
      currentStep._duration = Math.floor((Date.now() - currentStep._startedAt) / 1000);
    }
  }
  message.executionState = "failed";
  message.executionOpen = true;
  renderChat();
}

async function readAgentEventStream(response, message, requestId) {
  if (!_isCurrentRequest(requestId)) {
    return;
  }
  if (!response.ok) {
    let detail = "请求失败";
    try {
      const data = await response.json();
      if (!_isCurrentRequest(requestId)) {
        return;
      }
      detail = data.detail || detail;
    } catch (_error) {
      // Keep the safe default for non-JSON HTTP errors.
    }
    if (!_isCurrentRequest(requestId)) {
      return;
    }
    throw new Error(detail);
  }
  if (!response.body) {
    throw new Error("浏览器未提供流式响应体");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let doneReceived = false;

  function handleEventBlock(block) {
    if (!_isCurrentRequest(requestId)) {
      return;
    }
    const lines = block.split("\n");
    let eventName = "message";
    const dataLines = [];
    for (const line of lines) {
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trimStart());
      }
    }
    if (dataLines.length === 0) {
      return;
    }

    const data = JSON.parse(dataLines.join("\n"));
    if (eventName === "status") {
      updateExecutionProcess(message, data);
    } else if (eventName === "delta") {
      message.content += data.text || "";
      renderChat();
    } else if (eventName === "done") {
      doneReceived = true;
      applyStreamingDone(message, data);
    } else if (eventName === "error") {
      markExecutionFailed(message);
      throw new Error(data.message || "生成回答时发生错误");
    }
  }

  while (true) {
    if (!_isCurrentRequest(requestId)) {
      void reader.cancel().catch(() => {});
      return;
    }
    const { value, done } = await reader.read();
    if (!_isCurrentRequest(requestId)) {
      void reader.cancel().catch(() => {});
      return;
    }
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    buffer = buffer.replaceAll("\r\n", "\n");

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      if (block.trim()) {
        handleEventBlock(block);
      }
      if (!_isCurrentRequest(requestId)) {
        void reader.cancel().catch(() => {});
        return;
      }
      boundary = buffer.indexOf("\n\n");
    }

    if (done) {
      if (buffer.trim()) {
        handleEventBlock(buffer);
      }
      break;
    }
  }

  if (!_isCurrentRequest(requestId)) {
    return;
  }
  if (!doneReceived) {
    throw new Error("流式响应提前结束");
  }
}

async function onSubmit(event) {
  event.preventDefault();
  _invalidateActiveRequest();
  _clearAllTimers();

  const text = chatInput.value.trim();
  if (!text) {
    setChatStatus("请输入消息", "error");
    return;
  }

  const imageFile = chatImageInput.files[0];
  const requestId = ++_requestGeneration;
  const controller = new AbortController();
  _activeRequest = { requestId, controller };
  addUserMessage(text, imageFile);
  let assistantMessage = null;
  sendChatButton.disabled = true;
  setChatStatus("回复中", "loading");

  try {
    const payload = await buildPayload();
    if (!_isCurrentRequest(requestId)) {
      return;
    }
    assistantMessage = startStreamingAssistantMessage();
    const response = await fetch("/api/agent/query/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    if (!_isCurrentRequest(requestId)) {
      return;
    }
    await readAgentEventStream(response, assistantMessage, requestId);
    if (!_isCurrentRequest(requestId)) {
      return;
    }
    chatInput.value = "";
    chatImageInput.value = "";
    renderPreview(chatImagePreview, null, "本轮未选择图片");
    setChatStatus("已完成", "success");
  } catch (error) {
    if (!_isCurrentRequest(requestId) || error?.name === "AbortError") {
      return;
    }
    const message = error instanceof Error ? error.message : "请求失败";
    if (!assistantMessage) {
      assistantMessage = startStreamingAssistantMessage();
    }
    markExecutionFailed(assistantMessage);
    assistantMessage.content = assistantMessage.content
      ? `${assistantMessage.content}\n\n请求中断：${message}`
      : `请求失败：${message}`;
    renderChat();
    setChatStatus("请求失败", "error");
  } finally {
    if (_isCurrentRequest(requestId)) {
      _activeRequest = null;
      sendChatButton.disabled = false;
    }
  }
}

function clearChat() {
  _invalidateActiveRequest();
  _clearAllTimers();
  chatState.messages = [];
  chatInput.value = "";
  chatImageInput.value = "";
  renderPreview(chatImagePreview, null, "本轮未选择图片");
  renderChat();
  setChatStatus("空闲");
  sendChatButton.disabled = false;
}

chatForm.addEventListener("submit", onSubmit);
chatTimeline.addEventListener(
  "toggle",
  (event) => {
    const details = event.target;
    if (!details.classList.contains("execution-process")) {
      return;
    }
    const message = chatState.messages[Number(details.dataset.messageIndex)];
    if (!message || !message.executionSteps) {
      return;
    }
    if (message.executionState === "running" && !details.open) {
      details.open = true;
      return;
    }
    message.executionOpen = details.open;
  },
  true
);
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
