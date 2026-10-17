# Task: Responsive Design & Layout Improvements

## Context
The current GGena frontend uses fixed widths and prevents scrolling, which causes issues on mobile devices and small viewports.

## Objective
Implement a responsive design strategy to ensure the UI works well across all device sizes.

## Requirements
1. **Flexible Sidebar**: 
   - Replace the hardcoded `width: 350px` for `.settings-panel` with relative units (e.g., `%`, `vw`, or `rem`).
2. **Overflow Management**: 
   - Remove `body { overflow: hidden; }` to allow scrolling when content exceeds the viewport height, especially on mobile.
3. **Mobile-First Layout**: 
   - Use CSS Media Queries to implement a stacked layout or a "Settings Drawer" (toggled via hamburger menu) for tablet and mobile devices.
4. **Flexible Units**: 
   - Audit the CSS and replace fixed `px` values with flexible units where appropriate.

## Constraints
- Use Vanilla JS/ES6+.
- Do not introduce heavy frameworks.
- Maintain existing functionality.

## Acceptance Criteria
- [ ] The settings panel adapts to different screen widths.
- [ ] Users can scroll through all controls on mobile devices.
- [ ] A mobile-friendly layout (e.g., drawer or stacked) is implemented for small screens.
- [ ] UI elements scale appropriately without breaking the layout.
