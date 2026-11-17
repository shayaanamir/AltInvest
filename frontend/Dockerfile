# Dev image: runs the Vite dev server with HMR. For production see Dockerfile.prod.
# Build from frontend/:  docker build -t altinvest-frontend .

FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .

EXPOSE 5173

# --host is required so the dev server is reachable from outside the container
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
