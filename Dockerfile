# Build the React/Vite frontend
FROM node:22-alpine AS frontend
WORKDIR /app/webapp
COPY webapp/package*.json ./
RUN npm install
COPY webapp/ ./
RUN npm run build

# Run the FastAPI backend and serve the built frontend
FROM python:3.12-slim AS app
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . ./
COPY --from=frontend /app/webapp/dist ./webapp/dist
EXPOSE 8000
CMD ["python", "run_all.py"]
