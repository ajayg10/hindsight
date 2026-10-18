import fs from "fs";

let code = fs.readFileSync("frontend/legacy/app.js", "utf8");

// Add ts-nocheck and import cytoscape
const header = `// @ts-nocheck
import cytoscape from "cytoscape";

`;

// Replace currentSessionId initialization to guard sessionStorage
code = code.replace(
  'let currentSessionId = sessionStorage.getItem("hindsight_session_id") || null;',
  'let currentSessionId = typeof window !== "undefined" ? sessionStorage.getItem("hindsight_session_id") : null;'
);

// Replace DOMContentLoaded block
const domLoadedRegex = /document\.addEventListener\("DOMContentLoaded",\s*async\s*\(\)\s*=>\s*\{[\s\S]*?setInterval\(\(\)\s*=>\s*updateLiveStats\(activeTenant\),\s*4000\);\s*\}\);/;

const replacementInit = `let statsInterval: any = null;

export function initWarRoom(): () => void {
  if (typeof window === "undefined") return () => {};

  (async () => {
    try {
      await ensureSession(activeTenant);
      await initCytoscape(activeTenant);
      initEventStream();
      initControls();
      updateLiveStats(activeTenant);
      statsInterval = setInterval(() => updateLiveStats(activeTenant), 4000);
    } catch (err) {
      console.error("War room initialization error:", err);
    }
  })();

  return () => {
    if (statsInterval) {
      clearInterval(statsInterval);
      statsInterval = null;
    }
    if (evtSource) {
      try {
        evtSource.close();
      } catch (e) {}
      evtSource = null;
    }
    if (cy) {
      try {
        cy.destroy();
      } catch (e) {}
      cy = null;
    }
    eventCount = 0;
  };
}`;

if (!domLoadedRegex.test(code)) {
  console.error("Could not find DOMContentLoaded regex match in app.js");
  process.exit(1);
}

code = code.replace(domLoadedRegex, replacementInit);

const finalCode = header + code;

fs.writeFileSync("frontend/src/warroom/warroom-logic.ts", finalCode, "utf8");
console.log("warroom-logic.ts written successfully. Size:", finalCode.length);
