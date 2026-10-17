# Task: Modular Structure Migration

## Context
The current frontend implementation is moving towards a more scalable architecture to support future generator types (audio, video). The current single-file approach needs to be broken down into modules.

## Objective
Migrate the existing monolithic JS/CSS files into the proposed modular structure.

## Proposed Structure:
```text
src/app/frontend/
├── index.html          # Main entry point
├── assets/             # Images, icons, fonts
├── css/
│   ├── main.css        # Entry point (imports others)
│   ├── variables.css   # Design tokens (--accent-color, etc.)
│   ├── layout.css      # Grid and flexbox structures
│   └── components/     # Modular component styles
│       ├── buttons.css
│       ├── inputs.css
│       └── progress.css
└── js/
    ├── main.js         # Orchestrator / App entry
    ├── api.js          # WebSocket & HTTP communication
    ├── ui.js           # DOM manipulation & event listeners
    └── utils.js        # Helper functions (zoom, formatting)
```

## Requirements
1. **CSS Modularization**: 
   - Split the existing CSS into `variables.css`, `layout.css`, and component-specific files under `css/components/`.
   - Use `main.css` as the entry point that imports all other styles.
2. **JS Modularization**: 
   - Break down the monolithic JS file into `main.js`, `api.js`, `ui.js`, and `utils.js`.
   - Ensure proper module imports/exports (ES Modules).

## Constraints
- Use Vanilla JS/ES6+.
- Do not introduce heavy frameworks.
- Maintain existing functionality.

## Acceptance Criteria
- [ ] The application is successfully refactored into the proposed directory structure.
- [ ] All styles and scripts are correctly imported and functional via `main.css` and `main.js`.
- [ ] No breakage in existing features during the migration.
