# Fact Check Extension

This is the browser extension component for the Fact Check project.

## Development

1. Install dependencies: `npm install`
2. Start development watch mode: `npm run dev`
3. Build for production: `npm run build`
4. Typecheck: `npm run typecheck`
5. Lint: `npm run lint`

## How to Load Unpacked in Chrome

1. Build the extension or run dev watch mode so the `dist/` directory is generated.
2. Open Google Chrome and go to `chrome://extensions/`.
3. Enable **Developer mode** using the toggle switch in the top right corner.
4. Click the **Load unpacked** button.
5. Select the `dist/` folder generated inside this `extension/` directory.
6. The extension is now loaded! You can pin it and click the icon to open the side panel, and navigate to Facebook to see the content script logs.
