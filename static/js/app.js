// Mentalyze Unified Frontend Application

// Application State
const appState = {
  user: null,
  currentView: "home",
  isAssessmentActive: false,
  moodHistory: [],
  darkMode: false,
  voiceEnabled: false,
  voiceController: null,
  responses: [],
  voiceActive: false,
  currentQuestionIndex: 0,
};

// Allow same script to run on pages that do or do not define BACKEND_URL globally.
const API_BASE_URL =
  typeof window !== "undefined" && typeof window.BACKEND_URL === "string"
    ? window.BACKEND_URL
    : "";

const SUPPORTED_VIEWS = new Set([
  "home",
  "why-us",
  "assessment",
  "chat",
  "voice-chat",
  "mood",
]);

function isSupportedView(value) {
  return SUPPORTED_VIEWS.has(value);
}

function normalizeView(rawView, fallback = "home") {
  const value = String(rawView || "")
    .trim()
    .toLowerCase();
  return isSupportedView(value) ? value : fallback;
}

function getViewFromHref(href) {
  if (!href) {
    return "home";
  }

  const trimmedHref = String(href).trim();
  if (trimmedHref.startsWith("#")) {
    return normalizeView(trimmedHref.slice(1));
  }

  try {
    const parsedUrl = new URL(trimmedHref, window.location.origin);
    const pathView = parsedUrl.pathname.replace(/^\/+|\/+$/g, "");
    return normalizeView(pathView);
  } catch {
    const pathView = trimmedHref.replace(/^\/+|\/+$/g, "");
    return normalizeView(pathView);
  }
}

function resolveInitialViewFromLocation() {
  const hashView = String(window.location.hash || "")
    .replace(/^#/, "")
    .trim()
    .toLowerCase();
  if (isSupportedView(hashView)) {
    return hashView;
  }

  const pathView = String(window.location.pathname || "")
    .replace(/^\/+|\/+$/g, "")
    .trim()
    .toLowerCase();
  return normalizeView(pathView);
}

function setupNavbarAutoCollapse() {
  const navbarCollapse =
    document.getElementById("navbarNav") ||
    document.getElementById("navbarTogglerDemo01");

  if (!navbarCollapse || typeof bootstrap === "undefined" || !bootstrap.Collapse) {
    return;
  }

  const bsCollapse = new bootstrap.Collapse(navbarCollapse, { toggle: false });
  navbarCollapse.querySelectorAll(".nav-link").forEach((navLink) => {
    navLink.addEventListener("click", () => {
      const toggler = document.querySelector(".navbar-toggler");
      if (toggler && window.getComputedStyle(toggler).display !== "none") {
        bsCollapse.hide();
      }
    });
  });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

// Auto-collapse Bootstrap navbar on nav link click (for mobile)
document.addEventListener("DOMContentLoaded", function () {
  setupNavbarAutoCollapse();
});

// Voice Controller
class VoiceController {
  constructor() {
    this.speechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    this.speechSynthesis = window.speechSynthesis || null;
    this.recognition = null;
    this.isListening = false;
    this.voice = null;
    if (this.speechSynthesis) {
      this.loadVoices();
    }
  }

  loadVoices() {
    if (!this.speechSynthesis) {
      return;
    }
    const voices = this.speechSynthesis.getVoices();
    if (voices.length > 0) {
      // Select a preferred voice, e.g., a female English voice with natural accent
      this.voice = voices.find(
        (v) =>
          v.lang.startsWith("en") &&
          (v.name.toLowerCase().includes("female") ||
            v.name.toLowerCase().includes("google us english") ||
            v.name.toLowerCase().includes("zira") ||
            v.name.toLowerCase().includes("susan")),
      );
      if (!this.voice) {
        this.voice = voices[0];
      }
    } else {
      // Voices not loaded yet, try again after a delay
      window.speechSynthesis.onvoiceschanged = () => {
        this.loadVoices();
      };
    }
  }

  init() {
    if (!this.speechRecognition) {
      console.warn("Speech Recognition not supported");
      return false;
    }

    this.recognition = new this.speechRecognition();
    this.recognition.continuous = false;
    this.recognition.interimResults = false;
    this.recognition.lang = "en-US";

    return true;
  }

  startListening(callback) {
    if (!this.recognition) return;

    this.recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      callback(transcript);
    };

    this.recognition.start();
    this.isListening = true;
  }

  stopListening() {
    if (this.recognition && this.isListening) {
      this.recognition.stop();
      this.isListening = false;
    }
  }

  speak(text) {
    if (!this.speechSynthesis) return;

    // Cancel any ongoing speech to avoid overlapping
    if (this.speechSynthesis.speaking) {
      this.speechSynthesis.cancel();
    }

    const utterance = new SpeechSynthesisUtterance(text);
    if (this.voice) {
      utterance.voice = this.voice;
    }
    utterance.rate = 1.1; // Slightly slower for naturalness
    utterance.pitch = 1.1; // Slightly higher pitch for warmth
    utterance.volume = 1;

    this.speechSynthesis.speak(utterance);
  }
}

// Initialize voice controller
appState.voiceController = new VoiceController();

// Navigation setup
function setupNavigation() {
  document.querySelectorAll(".nav-link").forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const view = getViewFromHref(link.getAttribute("href"));
      showView(view, { userInitiated: true, updateHistory: true });
    });
  });
}
// Show view - comprehensive version with navbar updating and smooth scroll
let appScriptInitialLoad = true;
function showView(view, options = {}) {
  const {
    userInitiated = true,
    updateHistory = true,
    replaceHistory = false,
  } = options;
  const normalizedView = normalizeView(view);
  appState.currentView = normalizedView;

  // Hide all sections
  document.querySelectorAll(".section").forEach((section) => {
    section.style.display = "none";
  });

  // Show the selected section
  const viewElement = document.getElementById(normalizedView);
  if (viewElement) {
    viewElement.style.display = "block";
  }

  // Update navbar active state
  document.querySelectorAll(".nav-link").forEach((link) => {
    link.classList.remove("active");
    const hrefView = getViewFromHref(link.getAttribute("href"));
    if (hrefView === normalizedView) {
      link.classList.add("active");
    }
  });

  if (updateHistory && typeof window.history !== "undefined") {
    const targetPath = normalizedView === "home" ? "/" : `/${normalizedView}`;
    if (window.location.pathname !== targetPath || window.location.hash) {
      if (replaceHistory) {
        window.history.replaceState({ view: normalizedView }, "", targetPath);
      } else {
        window.history.pushState({ view: normalizedView }, "", targetPath);
      }
    }
  }

  // Only scroll to top on user-initiated view changes, not initial route restore.
  if (userInitiated && !appScriptInitialLoad) {
    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  }

  // If showing chat, focus on input
  if (normalizedView === "chat") {
    setTimeout(() => {
      const chatInput = document.getElementById("chat-input");
      if (chatInput) chatInput.focus();
    }, 300);
  }
}
window.showView = showView;

// Load initial data
function loadInitialData() {
  const savedMoodHistory =
    typeof safeLocalGet === "function"
      ? safeLocalGet("moodHistory")
      : localStorage.getItem("moodHistory");
  if (savedMoodHistory) {
    try {
      appState.moodHistory = JSON.parse(savedMoodHistory);
    } catch (e) {
      appState.moodHistory = [];
    }
  }
}

// Chat Module
function initChat() {
  const chatInput = document.getElementById("chat-input");
  const sendBtn = document.getElementById("send-btn");
  const chatMessages = document.getElementById("chat-messages");
  if (!chatInput || !sendBtn || !chatMessages) {
    return;
  }

  let isSending = false;

  sendBtn.addEventListener("click", sendMessage);
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendMessage();
    }
  });

  function addChatMessage(sender, text) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${sender}-message`;
    if (sender === "ai") {
      // Parse markdown and set as HTML
      messageDiv.innerHTML = marked.parse(text || "");
    } else {
      // For user messages, set as plain text for safety
      messageDiv.textContent = text;
    }
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  async function sendMessage() {
    if (isSending) return;

    const message = chatInput.value.trim();
    if (!message) return;

    // Allow all messages without restriction

    isSending = true;
    sendBtn.disabled = true;
    sendBtn.textContent = "Loading...";

    addChatMessage("user", message);
    chatInput.value = "";

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });

      if (!response.ok) throw new Error(response.statusText);

      const data = await response.json();
      addChatMessage("ai", data.reply);
    } catch (error) {
      addChatMessage("ai", `⚠️ Error: ${error.message}`);
    } finally {
      isSending = false;
      sendBtn.disabled = false;
      sendBtn.textContent = "Send";
    }
  }
}

// Assessment Module
async function initAssessment() {
  const questionsContainer = document.getElementById("assessment-questions");
  const startGeneralBtn = document.getElementById(
    "start-general-assessment-btn",
  );
  const startDetailedBtn = document.getElementById(
    "start-detailed-assessment-btn",
  );
  const progressText = document.getElementById("progress-text");
  const prevBtn = document.getElementById("prev-question-btn");
  const nextBtn = document.getElementById("next-question-btn");
  const descriptionDiv = document.getElementById("assessment-description");
  const navigationDiv = document.getElementById("assessment-navigation");
  const progressContainer = document.querySelector(".progress-container");

  if (
    !questionsContainer ||
    !startGeneralBtn ||
    !startDetailedBtn ||
    !prevBtn ||
    !nextBtn ||
    !descriptionDiv ||
    !navigationDiv ||
    !progressContainer ||
    !progressText
  ) {
    return;
  }

  let assessmentQuestions = [];
  let currentAssessmentType = "general";
  const assessmentCache = {
    general: null,
    detailed: null,
  };

  function setStartButtonsLoading(isLoading) {
    startGeneralBtn.disabled = isLoading;
    startDetailedBtn.disabled = isLoading;
  }

  async function fetchAssessmentQuestions(type) {
    const normalizedType = type === "detailed" ? "detailed" : "general";
    if (assessmentCache[normalizedType]) {
      return assessmentCache[normalizedType];
    }

    const response = await fetch(
      `/api/assessment_questions?type=${encodeURIComponent(normalizedType)}`,
    );
    if (!response.ok) {
      throw new Error(`Failed to load ${normalizedType} assessment`);
    }

    const payload = await response.json();
    if (!Array.isArray(payload) || payload.length === 0) {
      throw new Error("No questions available right now");
    }

    assessmentCache[normalizedType] = payload;
    return payload;
  }

  function updateProgress(index) {
    const denominator = Math.max(assessmentQuestions.length, 1);
    const progress = ((index + 1) / denominator) * 100;
    document.getElementById("assessment-progress-bar").style.width =
      `${progress}%`;
    progressText.textContent = `${Math.round(progress)}%`;
  }

  function updateNextButtonLabel(index) {
    const isLastQuestion = index === assessmentQuestions.length - 1;
    nextBtn.innerHTML = isLastQuestion
      ? 'Finish <i class="fas fa-check ms-2"></i>'
      : 'Next <i class="fas fa-arrow-right ms-2"></i>';
  }

  function getSavedResponse(index) {
    return appState.responses[index] || null;
  }

  function resetAssessmentUI() {
    descriptionDiv.style.display = "block";
    startGeneralBtn.style.display = "inline-block";
    startDetailedBtn.style.display = "inline-block";
    questionsContainer.style.display = "none";
    navigationDiv.style.display = "none";
    progressContainer.style.display = "none";
    progressText.textContent = "0%";
    document.getElementById("assessment-progress-bar").style.width = "0%";
    prevBtn.disabled = true;
    nextBtn.disabled = true;
    nextBtn.innerHTML = 'Next <i class="fas fa-arrow-right ms-2"></i>';
  }

  async function startAssessment(type) {
    currentAssessmentType = type === "detailed" ? "detailed" : "general";
    setStartButtonsLoading(true);

    try {
      assessmentQuestions = await fetchAssessmentQuestions(currentAssessmentType);
    } catch (error) {
      alert(`Error loading assessment questions: ${error.message}`);
      resetAssessmentUI();
      setStartButtonsLoading(false);
      return;
    }

    appState.responses = new Array(assessmentQuestions.length).fill(null);
    appState.currentView = "assessment";
    appState.currentQuestionIndex = 0;
    descriptionDiv.style.display = "none";
    startGeneralBtn.style.display = "none";
    startDetailedBtn.style.display = "none";
    questionsContainer.style.display = "block";
    navigationDiv.style.display = "flex";
    progressContainer.style.display = "block";
    setStartButtonsLoading(false);
    renderQuestion(0);
  }

  startGeneralBtn.addEventListener("click", (e) => {
    e.preventDefault();
    startAssessment("general");
  });

  startDetailedBtn.addEventListener("click", (e) => {
    e.preventDefault();
    startAssessment("detailed");
  });

  prevBtn.addEventListener("click", () => {
    if (appState.currentQuestionIndex > 0) {
      renderQuestion(appState.currentQuestionIndex - 1);
    }
  });

  nextBtn.addEventListener("click", () => {
    const saved = getSavedResponse(appState.currentQuestionIndex);
    if (!saved || !saved.answer) {
      return;
    }

    if (appState.currentQuestionIndex < assessmentQuestions.length - 1) {
      renderQuestion(appState.currentQuestionIndex + 1);
      return;
    }

    showCompletion();
  });

  function renderQuestion(index) {
    appState.currentQuestionIndex = index;
    const q = assessmentQuestions[index];
    const savedResponse = getSavedResponse(index);
    const isOpenTextQuestion =
      q?.allow_text === true ||
      !Array.isArray(q?.options) ||
      q.options.length === 0 ||
      (q.options.length === 1 &&
        String(q.options[0]).toLowerCase().includes("open-ended"));

    if (isOpenTextQuestion) {
      questionsContainer.innerHTML = `
        <div class="question-card">
          <h5>Question ${index + 1} of ${assessmentQuestions.length}</h5>
          <p class="lead mb-4">${escapeHtml(q?.question || "")}</p>
          <textarea
            id="assessment-open-answer"
            class="form-control"
            rows="4"
            placeholder="Type your response..."
          >${escapeHtml(savedResponse?.answer || "")}</textarea>
        </div>
      `;

      const openInput = document.getElementById("assessment-open-answer");
      const commitOpenResponse = () => {
        const answer = openInput.value.trim();
        appState.responses[index] = {
          question: q.question,
          answer,
          score: answer ? 1 : null,
        };
        nextBtn.disabled = !answer;
      };

      openInput.addEventListener("input", commitOpenResponse);
      openInput.addEventListener("blur", commitOpenResponse);
      commitOpenResponse();
    } else {
      questionsContainer.innerHTML = `
        <div class="question-card">
          <h5>Question ${index + 1} of ${assessmentQuestions.length}</h5>
          <p class="lead mb-4">${escapeHtml(q.question)}</p>
          <div class="options">
            ${q.options
              .map((opt, i) => {
                const selectedClass = savedResponse?.answer === opt ? "active" : "";
                return `
                  <button
                    class="option-btn ${selectedClass}"
                    data-value="${escapeHtml(opt)}"
                    data-index="${i}"
                    type="button"
                  >${escapeHtml(opt)}</button>
                `;
              })
              .join("")}
          </div>
        </div>
      `;

      document.querySelectorAll(".option-btn").forEach((button) => {
        button.addEventListener("click", () => {
          document
            .querySelectorAll(".option-btn")
            .forEach((b) => b.classList.remove("active"));
          button.classList.add("active");

          appState.responses[index] = {
            question: q.question,
            answer: button.getAttribute("data-value"),
            score: parseInt(button.getAttribute("data-index"), 10) + 1,
          };
          nextBtn.disabled = false;
        });
      });
    }

    updateProgress(index);
    updateNextButtonLabel(index);
    prevBtn.disabled = index === 0;
    nextBtn.disabled = !(savedResponse && savedResponse.answer);
  }

  function showCompletion() {
    const answeredCount = appState.responses.filter((item) => !!item?.answer).length;
    const showDetailedPrompt = currentAssessmentType === "general";

    questionsContainer.innerHTML = `
      <div class="question-card">
        <h5>Assessment Complete</h5>
        <p class="lead">You answered ${answeredCount} of ${assessmentQuestions.length} questions.</p>
        <p>Generate your personalized analysis when you're ready.</p>
        <div class="mt-3 d-flex flex-wrap gap-2">
          <button id="view-results-btn" class="btn btn-primary">
            <i class="fas fa-chart-line me-2"></i>View Results
          </button>
          ${
            showDetailedPrompt
              ? `<button id="continue-detailed-btn" class="btn btn-outline-primary">
                   <i class="fas fa-plus-circle me-2"></i>Take Detailed Check-In
                 </button>`
              : ""
          }
        </div>
      </div>
    `;

    progressText.textContent = "100%";
    document.getElementById("assessment-progress-bar").style.width = "100%";
    prevBtn.disabled = true;
    nextBtn.disabled = true;
    navigationDiv.style.display = "none";

    document
      .getElementById("view-results-btn")
      .addEventListener("click", showResults);

    const continueDetailedBtn = document.getElementById("continue-detailed-btn");
    if (continueDetailedBtn) {
      continueDetailedBtn.addEventListener("click", () => {
        startAssessment("detailed");
      });
    }
  }

  async function showResults() {
    const answers = assessmentQuestions.map((question, index) => {
      const response = appState.responses[index];
      return {
        question: question?.question || "",
        answer: response?.answer || "No response",
        score: response?.score ?? null,
        question_index: index,
      };
    });

    questionsContainer.innerHTML = `
      <div class="question-card">
        <h5>Your Assessment Results</h5>
        <p>Loading analysis...</p>
      </div>
    `;

    try {
      const response = await fetch("/api/assessment_analysis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          answers,
          assessment_type: currentAssessmentType,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const data = await response.json();

      if (!data.analysis) {
        throw new Error("No analysis received from server");
      }

      let analysisHtml = data.analysis;
      if (typeof marked !== "undefined" && marked.parse) {
        analysisHtml = marked.parse(data.analysis);
      }

      questionsContainer.innerHTML = `
        <div class="question-card">
          <h5>Your Assessment Analysis</h5>
          ${
            data.mood_logged
              ? '<p class="small text-muted mb-3">Mood tracker was updated from your assessment responses.</p>'
              : ""
          }
          <div class="analysis-content" id="analysis-content">${analysisHtml}</div>
          <div class="mt-4 d-flex flex-wrap gap-2">
            <button id="download-report" class="btn btn-primary">
              <i class="fas fa-download me-1"></i>Download Report
            </button>
            <button id="copy-analysis" class="btn btn-outline-primary">
              <i class="fas fa-copy me-1"></i>Copy Analysis
            </button>
            <button id="restart-assessment" class="btn btn-outline-primary">
              <i class="fas fa-redo me-1"></i>Restart Assessment
            </button>
          </div>
        </div>
      `;

      document
        .getElementById("restart-assessment")
        .addEventListener("click", () => {
          resetAssessmentUI();
          appState.responses = [];
        });

      document
        .getElementById("download-report")
        .addEventListener("click", () => {
          if (typeof window.jspdf !== "undefined" && window.jspdf.jsPDF) {
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF();
            const content =
              document.getElementById("analysis-content").innerText || data.analysis;
            const splitContent = doc.splitTextToSize(content, 180);
            doc.text(splitContent, 10, 10);
            doc.save("assessment_report.pdf");
          } else {
            const element = document.createElement("a");
            element.setAttribute(
              "href",
              "data:text/plain;charset=utf-8," + encodeURIComponent(data.analysis),
            );
            element.setAttribute("download", "assessment_report.txt");
            element.style.display = "none";
            document.body.appendChild(element);
            element.click();
            document.body.removeChild(element);
          }
        });

      document
        .getElementById("copy-analysis")
        .addEventListener("click", async () => {
          const textToCopy =
            document.getElementById("analysis-content").innerText || data.analysis;
          try {
            await navigator.clipboard.writeText(textToCopy);
            const copyBtn = document.getElementById("copy-analysis");
            if (copyBtn) {
              copyBtn.innerHTML = '<i class="fas fa-check me-1"></i>Copied';
              setTimeout(() => {
                copyBtn.innerHTML = '<i class="fas fa-copy me-1"></i>Copy Analysis';
              }, 1400);
            }
          } catch (error) {
            alert("Could not copy analysis automatically. Please copy it manually.");
          }
        });
    } catch (error) {
      questionsContainer.innerHTML = `
        <div class="question-card">
          <h5>Error Loading Results</h5>
          <p>Could not load analysis: ${error.message}</p>
          <button id="restart-assessment" class="btn btn-primary">Restart Assessment</button>
        </div>
      `;

      document
        .getElementById("restart-assessment")
        .addEventListener("click", () => {
          resetAssessmentUI();
          appState.responses = [];
        });
    }
  }

  resetAssessmentUI();
}

// Mood Module
function initMood() {
  // The main index page already ships an advanced mood tracker implementation
  // in its inline script. Keep this legacy module as a fallback for older pages.
  if (document.getElementById("mood-save-btn")) {
    if (
      typeof window.initializeMoodChart === "function" &&
      !window.__psyAIMoodInitialized
    ) {
      window.__psyAIMoodInitialized = true;
      Promise.resolve(window.initializeMoodChart()).catch((error) => {
        console.error("Mood tracker initialization failed:", error);
      });
    }
    return;
  }

  const happyBtn = document.getElementById("happy-btn");
  const sadBtn = document.getElementById("sad-btn");
  const anxiousBtn = document.getElementById("anxious-btn");
  const moodSection = document.getElementById("mood");
  if (!happyBtn || !sadBtn || !anxiousBtn || !moodSection) {
    return;
  }

  const moodChartCanvas = document.createElement("canvas");
  moodChartCanvas.id = "mood-chart";
  moodChartCanvas.style.maxWidth = "600px";
  moodChartCanvas.style.marginTop = "20px";

  moodSection.appendChild(moodChartCanvas);

  let moodChart = null;
  let moodCounts = { happy: 0, sad: 0, anxious: 0 };

  happyBtn.addEventListener("click", () => recordMood("happy"));
  sadBtn.addEventListener("click", () => recordMood("sad"));
  anxiousBtn.addEventListener("click", () => recordMood("anxious"));

  function recordMood(mood) {
    const now = new Date();

    appState.moodHistory.push({
      mood,
      timestamp: now.toISOString(),
    });

    // Increment mood count dynamically
    if (moodCounts.hasOwnProperty(mood)) {
      moodCounts[mood]++;
    }

    saveMoodHistory();
    updateMoodChart();

    // Provide user feedback on mood selection
    // alert(`Mood recorded: ${mood}`);

    // In a real app, send mood to backend here
  }

  function saveMoodHistory() {
    if (typeof safeLocalSet === "function") {
      safeLocalSet("moodHistory", JSON.stringify(appState.moodHistory));
    } else {
      try {
        localStorage.setItem(
          "moodHistory",
          JSON.stringify(appState.moodHistory),
        );
      } catch (e) {
        // fallback: ignore storage errors
      }
    }
  }

  function updateMoodChart() {
    const total = moodCounts.happy + moodCounts.sad + moodCounts.anxious;
    if (!total) {
      return;
    }
    const data = {
      labels: ["Happy", "Sad", "Anxious"],
      datasets: [
        {
          label: "Mood Distribution",
          data: [
            ((moodCounts.happy / total) * 100).toFixed(1),
            ((moodCounts.sad / total) * 100).toFixed(1),
            ((moodCounts.anxious / total) * 100).toFixed(1),
          ],
          backgroundColor: ["#28a745", "#17a2b8", "#ffc107"],
          hoverOffset: 30,
        },
      ],
    };

    const config = {
      type: "doughnut",
      data: data,
      options: {
        responsive: true,
        plugins: {
          tooltip: {
            callbacks: {
              label: function (context) {
                return `${context.label}: ${context.parsed}%`;
              },
            },
          },
          legend: {
            position: "bottom",
            labels: {
              font: {
                size: 14,
              },
            },
          },
        },
      },
    };

    if (moodChart) {
      // Update existing chart data and options dynamically
      moodChart.data.labels = data.labels;
      moodChart.data.datasets = data.datasets;
      moodChart.options = config.options;
      moodChart.update();
    } else {
      moodChart = new Chart(document.getElementById("mood-chart"), config);
    }

    // Update mood feedback text
    const feedbackDiv = document.getElementById("mood-feedback");
    if (appState.moodHistory.length > 0) {
      const lastMood =
        appState.moodHistory[appState.moodHistory.length - 1].mood;
      feedbackDiv.textContent = `Last mood recorded: ${lastMood}`;
    } else {
      feedbackDiv.textContent = "";
    }
  }

  // Load existing mood history and render chart
  if (appState.moodHistory.length > 0) {
    // Recalculate moodCounts from history on load
    moodCounts = { happy: 0, sad: 0, anxious: 0 };
    appState.moodHistory.forEach((entry) => {
      if (moodCounts.hasOwnProperty(entry.mood)) {
        moodCounts[entry.mood]++;
      }
    });
    updateMoodChart();
  }
}

//Dark Mode Toggle
function initDarkMode() {
  const darkModeToggle = document.getElementById("dark-mode-toggle");
  if (!darkModeToggle) {
    return;
  }

  // Dark mode interaction is managed by index.html's centralized theme script.
  // Here we only keep app state synchronized.
  appState.darkMode = document.documentElement.getAttribute("data-theme") === "dark";
}

function initApp() {
  appState.voiceEnabled = appState.voiceController.init();
  const inlineControllerPresent = typeof window.sendChatMessage === "function";

  initDarkMode();
  if (!inlineControllerPresent) {
    initChat();
  }
  initAssessment();
  initMood();

  setupNavigation();
  window.addEventListener("popstate", () => {
    showView(resolveInitialViewFromLocation(), {
      userInitiated: false,
      updateHistory: false,
    });
  });

  if (!inlineControllerPresent) {
    // Emergency button event listener
    const emergencyBtn = document.getElementById("emergency-btn");
    if (emergencyBtn) {
      emergencyBtn.addEventListener("click", async () => {
        try {
          const response = await fetch("/api/emergency_alert", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ timestamp: new Date().toISOString() }),
          });
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          alert("Emergency alert sent successfully!");
        } catch (error) {
          alert("Failed to send emergency alert: " + error.message);
        }
      });
    }
  }

  // Voice Chat Socket.io Integration
  if (appState.voiceEnabled && !inlineControllerPresent) {
    const socket = io();

    const startVoiceChatBtn = document.getElementById("start-voice-chat-btn");
    const voiceChatMessages = document.getElementById("voice-chat-messages");

    // Safety check: only proceed if elements exist
    if (!startVoiceChatBtn || !voiceChatMessages) {
      console.warn(
        "Voice chat elements not found in DOM. Voice chat feature disabled.",
      );
    } else {
      function appendVoiceChatMessage(sender, text) {
        const messageDiv = document.createElement("div");
        messageDiv.className = `message ${sender}-message`;

        if (sender === "ai") {
          messageDiv.innerHTML = marked.parse(text || "");
        } else {
          messageDiv.textContent = text;
        }
        voiceChatMessages.appendChild(messageDiv);
        voiceChatMessages.scrollTop = voiceChatMessages.scrollHeight;
      }

      startVoiceChatBtn.addEventListener("click", () => {
        if (appState.voiceActive) {
          appState.voiceController.stopListening();
          appState.voiceActive = false;
          startVoiceChatBtn.textContent = "Start Voice Chat";
        } else {
          appState.voiceController.startListening((transcript) => {
            appendVoiceChatMessage("user", transcript);
            socket.emit("voice_message", transcript);
          });
          appState.voiceActive = true;
          startVoiceChatBtn.textContent = "Listening... Click to Stop";
        }
      });

      socket.on("bot_response", (msg) => {
        const reply = msg && typeof msg === "object" ? msg.reply : msg;
        if (reply) {
          appendVoiceChatMessage("ai", reply);
          appState.voiceController.speak(reply);
        }
      });

      socket.on("error", (error) => {
        console.error("Socket.IO error:", error);
        appendVoiceChatMessage(
          "ai",
          "Sorry, there was a connection error. Please try again.",
        );
      });
    }
  }

  loadInitialData();
  showView(resolveInitialViewFromLocation(), {
    userInitiated: false,
    updateHistory: true,
    replaceHistory: true,
  });
  window.scrollTo({ top: 0, behavior: "auto" });
  appScriptInitialLoad = false; // Mark initial load as complete, now scroll on view changes
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  initApp();
  loadModelBenchmark();
});

// Function to fetch and display model benchmark data
async function loadModelBenchmark() {
  const container = document.getElementById("model-comparison-content");
  try {
    const response = await fetch("/api/model_benchmark");
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();

    if (data.error) {
      container.innerHTML = `<p>Error loading benchmark data: ${data.error}</p>`;
      return;
    }

    // Build HTML for model comparison
    let html = '<ul style="list-style: none; padding-left: 0;">';
    data.models.forEach((model) => {
      html += `
        <li style="margin-bottom: 15px;">
          <strong>${model.name}</strong><br/>
          Average Response Time: <strong>${
            model.average_response_time_ms
          } ms</strong><br/>
          <em>${model.description}</em>
          <div style="background: #ddd; border-radius: 5px; overflow: hidden; margin-top: 5px; height: 15px; width: 100%;">
            <div style="background: #4a6fa5; height: 100%; width: ${Math.min(
              model.average_response_time_ms / 15,
              100,
            )}%;"></div>
          </div>
        </li>
      `;
    });
    html += "</ul>";
    html += `<p style="font-style: italic; margin-top: 10px;">${data.comparison_note}</p>`;

    container.innerHTML = html;
  } catch (error) {
    container.innerHTML = `<p>Error loading benchmark data: ${error.message}</p>`;
  }
}
