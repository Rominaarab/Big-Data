FROM node:22-bookworm-slim
ENV NODE_ENV=production PORT=8080
WORKDIR /app
COPY package.json index.js server.mjs test.mjs ./
RUN node --test test.mjs
USER node
EXPOSE 8080
CMD ["node", "server.mjs"]
