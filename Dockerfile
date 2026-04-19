# Node.js Dockerfile for BayLang AI
FROM node:24-slim

# Install apk
RUN apt-get update && apt-get upgrade -y && \
	apt-get install mc nano wget net-tools -y

# Make data directory
WORKDIR /app
RUN mkdir /data && chown node:node /data

# Copy package.json and package-lock.json
COPY src/package*.json ./

# Install dependencies
RUN npm ci --omit=dev

# Copy source code
COPY files /
COPY src /app

RUN chmod +x /etc/run.sh
RUN npm run build

# Switch to the created user
USER node

# Run the application
CMD ["/etc/run.sh"]