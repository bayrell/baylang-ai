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

# Build app
RUN npm run build

# Copy files
RUN echo "Copy files" && \
	chmod +x /etc/run.sh && \
	cp /app/lib/Runtime.ORM/bay/MySQL/Adapter.js \
		/app/lib/Runtime.ORM/nodejs/MySQL/Adapter.js && \
	cp /app/lib/Runtime.Web/bay/Express.js \
		/app/lib/Runtime.Web/nodejs/Express.js

# Switch to the created user
USER node

# Run the application
CMD ["/etc/run.sh"]