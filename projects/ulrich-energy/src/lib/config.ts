export const config = {
  litellm: {
    url:
      process.env.ATHANOR_LITELLM_URL ??
      process.env.LITELLM_URL ??
      "http://192.168.1.203:4000",
  },
  api: {
    baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "",
  },
} as const;
