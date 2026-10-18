import fs from "fs";

let css = fs.readFileSync("frontend/legacy/index.css", "utf8");

// Extract keyframes
const keyframeMatch = css.match(/@keyframes pulse-ring\s*\{[\s\S]*?\n\}/);
const keyframes = keyframeMatch ? keyframeMatch[0] : "";

// Remove keyframes from original
css = css.replace(/@keyframes pulse-ring\s*\{[\s\S]*?\n\}/, "");

// Extract :root content
const rootMatch = css.match(/:root\s*\{([\s\S]*?)\}/);
const rootVars = rootMatch ? rootMatch[1] : "";

// Remove :root
css = css.replace(/:root\s*\{([\s\S]*?)\}/, "");

// Remove * rule
css = css.replace(/\*\s*\{[\s\S]*?\}/, "");

// Remove body rule
css = css.replace(/body\s*\{[\s\S]*?\}/, "");

const output = `/* Scoped War Room CSS */
${keyframes}

.war-room {
${rootVars}

  background-color: var(--bg-base);
  color: var(--text-main);
  font-family: var(--font-sans);
  height: 100vh;
  width: 100vw;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
  -webkit-font-smoothing: antialiased;

  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }

${css}
}
`;

fs.writeFileSync("frontend/src/warroom/war-room.css", output, "utf8");
console.log("war-room.css written successfully. Size:", output.length);
