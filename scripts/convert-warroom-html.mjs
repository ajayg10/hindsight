import fs from "fs";

const html = fs.readFileSync("frontend/legacy/index.html", "utf8");

// Extract content between <body> and </body>
const bodyMatch = html.match(/<body>([\s\S]*?)<\/body>/i);
if (!bodyMatch) {
  console.error("No body found");
  process.exit(1);
}

let bodyContent = bodyMatch[1];

// Remove script tag
bodyContent = bodyContent.replace(/<script\s+src="\/static\/app\.js\?v=1\.1"><\/script>/i, "");

// Add missing closing tag for memory-modal before company-modal if present
if (bodyContent.includes('<div id="memory-modal"') && bodyContent.includes('<div id="company-modal"')) {
  const compIndex = bodyContent.indexOf('<!-- Company Brain Questions Modal');
  if (compIndex !== -1) {
    bodyContent = bodyContent.slice(0, compIndex) + '  </div>\n' + bodyContent.slice(compIndex);
  }
}

// Convert class= to className=
bodyContent = bodyContent.replace(/\bclass="/g, 'className="');

// Convert for= to htmlFor=
bodyContent = bodyContent.replace(/\bfor="/g, 'htmlFor="');

// Convert stroke-width to strokeWidth
bodyContent = bodyContent.replace(/\bstroke-width="/g, 'strokeWidth="');

// Convert self-closing tags: <input ...> to <input ... />
bodyContent = bodyContent.replace(/<input([^>]*[^\/])>/gi, '<input$1 />');

// Convert HTML comments to JSX comments
bodyContent = bodyContent.replace(/<!--([\s\S]*?)-->/g, '{/*$1*/}');

// Add Back to Hindsight link in topbar brand
const brandInsert = `<div className="brand">
        <a
          href="/"
          className="back-link"
          title="Return to Hindsight Landing Page"
          style={{
            display: "inline-flex",
            alignItems: "center",
            color: "#94a3b8",
            fontSize: "0.85rem",
            fontWeight: 500,
            textDecoration: "none",
            marginRight: "0.75rem",
            padding: "0.25rem 0.5rem",
            borderRadius: "4px",
            background: "rgba(255, 255, 255, 0.05)",
          }}
        >
          &larr; Hindsight
        </a>`;

bodyContent = bodyContent.replace('<div className="brand">', brandInsert);

const finalJsx = `"use client";

import React, { useEffect } from "react";
import { initWarRoom } from "./warroom-logic";

export default function WarRoomView() {
  useEffect(() => {
    const cleanup = initWarRoom();
    return () => {
      if (cleanup) cleanup();
    };
  }, []);

  return (
    <div className="war-room">
${bodyContent}
    </div>
  );
}
`;

fs.writeFileSync("frontend/src/warroom/WarRoomView.tsx", finalJsx, "utf8");
console.log("WarRoomView.tsx written successfully. Size:", finalJsx.length);
