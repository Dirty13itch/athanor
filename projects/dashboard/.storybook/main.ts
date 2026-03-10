import type { StorybookConfig } from "@storybook/nextjs-vite";
import { mergeConfig } from "vite";

const config: StorybookConfig = {
  stories: ["../src/**/*.stories.@(ts|tsx)"],
  addons: ["@storybook/addon-docs", "@storybook/addon-a11y"],
  framework: {
    name: "@storybook/nextjs-vite",
    options: {},
  },
  docs: {
    autodocs: "tag",
  },
  async viteFinal(baseConfig) {
    return mergeConfig(baseConfig, {
      build: {
        // Storybook's static preview bundle is intentionally larger than the app bundle.
        chunkSizeWarningLimit: 1500,
        rollupOptions: {
          onwarn(warning, defaultHandler) {
            if (
              warning.code === "MODULE_LEVEL_DIRECTIVE" &&
              typeof warning.id === "string" &&
              warning.id.includes("node_modules/@radix-ui/") &&
              warning.message.includes('"use client"')
            ) {
              return;
            }

            defaultHandler(warning);
          },
        },
      },
    });
  },
};

export default config;
