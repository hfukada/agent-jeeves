FROM node:20.19-alpine3.22 AS builder

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
ARG PUBLIC_API_URL=http://localhost:8686
ENV PUBLIC_API_URL=$PUBLIC_API_URL
RUN npm run build

FROM node:20.19-alpine3.22

WORKDIR /app
COPY --from=builder /app/build ./build
COPY --from=builder /app/node_modules ./node_modules
COPY package.json .

ENV PORT=3000
EXPOSE 3000

CMD ["node", "build"]
