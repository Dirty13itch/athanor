import type { Preview } from "@storybook/react";
import "../src/app/globals.css";

const preview: Preview = {
  parameters: {
    backgrounds: {
      default: "athanor",
      values: [
        { name: "athanor", value: "#0b0b0b" },
      ],
    },
    controls: {
      expanded: true,
    },
    layout: "fullscreen",
  },
};

export default preview;
