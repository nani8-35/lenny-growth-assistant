FROM node:22-slim
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@11.19.0 --activate
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile --prod
COPY src ./src
COPY skills ./skills
ENV HOST=0.0.0.0
USER node
EXPOSE 3001
CMD ["node","src/server.mjs"]
