# Task: Error Handling & Feedback Enhancements

## Context
The current application uses intrusive browser `alert()` calls for errors and lacks subtle visual feedback for ongoing processes or connection changes.

## Objective
Replace disruptive alerts with a modern toast notification system and improve real-time feedback.

## Requirements
1. **Toast Notifications**: 
   - Implement a lightweight toast notification system (a small div that slides in/out) to replace all `alert()` calls for errors and successes.
2. **Enhanced Progress Visualization**: 
   - Add a "pulse" animation to the progress bar when it is active to indicate ongoing work.
3. **Connection Status Feedback**: 
   - Improve visual feedback for connection status changes (e.g., a pulsing dot or subtle animation when reconnecting).

## Constraints
- Use Vanilla JS/ES6+.
- Do not introduce heavy frameworks.
- Maintain existing functionality.

## Acceptance Criteria
- [ ] Errors and successes are shown via non-intrusive toast notifications instead of `alert()`.
- [ ] The progress bar visually indicates activity through animation.
- [ ] Connection status changes (like reconnecting) are clearly communicated with subtle visual cues.
