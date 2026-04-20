# Feature Usage Guide

This file explains how to use each major feature in PsyAI.

## 1. Home

- Open `http://localhost:5000`.
- Home includes:
  - Hero quick actions (chat, assessment, mood tracker)
  - KPI cards
  - "Start In 30 Seconds" quick action board
- You can use the floating back-to-top button when scrolling.

## 2. Why Us Page

- Open the `Why Us` tab from navbar.
- Review differentiators and side-by-side comparison with typical chatbot apps.
- Useful during project demonstration/presentation.

## 3. Assessment

### Quick Assessment (Recommended for most users)

1. Open `Assessment`.
2. Click `Quick Assessment (8 Questions)`.
3. Select one option per question.
4. Use `Previous` and `Next`.
5. Click `Finish` on the last question.
6. Click `View Results` to generate AI analysis.

### Detailed Check-In

1. Open `Assessment`.
2. Click `Detailed Check-In (14 Questions)`.
3. Complete responses.
4. Click `View Results`.

### Assessment Output Actions

- Download report (PDF when jsPDF is available, text fallback otherwise).
- Copy analysis directly using `Copy Analysis` button.
- Restart assessment from the result view.
- Assessment completion contributes to auto mood tracking.

## 4. Chat

1. Open `Chat`.
2. Type message and press Enter or click Send.
3. Receive AI response.

Additional behavior:

- Crisis keywords are checked.
- Chat interactions contribute to auto mood tracking.

## 5. Voice Chat

1. Open `Voice Chat`.
2. Click microphone/start control.
3. Speak.
4. Wait for AI response.

Requirements:

- Browser with speech recognition support (best in Chrome/Edge).
- Microphone permission enabled.

Additional behavior:

- Voice transcript is handled as conversation input.
- Voice interactions contribute to auto mood tracking.

## 6. Mood Tracker

### Manual Mood Logging

1. Open `Mood Tracker`.
2. Set mood score, energy, and anxiety.
3. Add tags and optional journal text.
4. Click `Save mood entry`.

### AI Insights

1. Click `AI insights`.
2. App generates a reflective summary from recent entries.

### Export Data

- JSON export
- CSV export

### Auto-Tracked Mood Sources

Mood entries may be created from:

- Manual mood form (`source=manual`)
- Text chat (`source=chat`)
- Voice chat (`source=voice_chat`)
- Assessment results (`source=assessment_general` or `assessment_detailed`)

`Mood stats` displays source breakdown so users can see where trend data comes from.

## 7. Dark Mode

- Toggle using the moon/sun button in navbar.
- Dark mode is applied app-wide, including cards, forms, and comparison tables.

## 8. Emergency Support Flow

1. Click `Emergency` button.
2. Confirm in the prompt.
3. App triggers emergency alert endpoint.

Note:

- Current backend implementation logs the alert event.
- Can be extended later with actual SMS/email/contact integrations.

## 9. Model Benchmark Section

- On Home page, benchmark data is loaded from `static/data/model_benchmark.json`.
- Displayed as model performance comparison cards.

Optional update workflow:

- Run `model_benchmark_test.py` to regenerate benchmark JSON.

## 10. Troubleshooting

### Assessment not loading

- Ensure backend is running.
- Verify `/api/assessment_questions?type=general` returns data.

### AI responses failing

- Check `.env` for valid `TOGETHER_API_KEY`.
- Ensure internet access in runtime environment.

### Voice not working

- Verify microphone permissions.
- Use supported browser.

### Mood insights empty

- Log entries first.
- Retry `AI insights`.
