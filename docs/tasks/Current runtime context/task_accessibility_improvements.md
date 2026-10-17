# Task: Accessibility (a11y) Improvements

## Context
The current GGena frontend is a vanilla JavaScript application. It lacks proper accessibility features, making it difficult for screen reader users and keyboard-only users to interact with the UI.

## Objective
Improve the accessibility of the GGena frontend following the recommendations in the Frontend UI/UX Assessment Report.

## Requirements
1. **ARIA Roles**: 
   - Add `aria-live="polite"` to `#status-text` so updates are announced by screen readers.
   - Ensure the progress bar (`#progress-bar`) is accessible (e.g., using `role="progressbar"`, `aria-valuenow`, etc.).
2. **Descriptive Controls**: 
   - Add descriptive `aria-label` attributes to navigation buttons (e.g., `<` and `>` should have labels like "Previous Image" and "Next Image").
3. **Keyboard Focus Management**: 
   - Implement clear visual indicators for keyboard focus on all interactive elements.

## Constraints
- Use Vanilla JS/ES6+.
- Do not introduce heavy frameworks.
- Maintain existing functionality.

## Acceptance Criteria
- [ ] Screen readers announce status changes via `#status-text`.
- [ ] Progress bar is correctly identified as a progress bar by assistive technologies.
- [ ] Navigation buttons have meaningful labels for screen readers.
- [ ] Keyboard users can clearly see which element currently has focus.
