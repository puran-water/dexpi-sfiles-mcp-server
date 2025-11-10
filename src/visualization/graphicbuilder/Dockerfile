# GraphicBuilder Docker Image
# Production DEXPI P&ID renderer microservice
FROM openjdk:17-slim

# Install required packages
RUN apt-get update && \
    apt-get install -y \
    maven \
    git \
    python3 \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Clone and build GraphicBuilder
RUN git clone https://gitlab.com/dexpi/GraphicBuilder.git && \
    cd GraphicBuilder && \
    mvn clean package -DskipTests

# Install Python dependencies for service wrapper
RUN pip3 install --no-cache-dir \
    flask \
    httpx \
    lxml \
    pyyaml

# Copy service wrapper script
COPY graphicbuilder-service.py /app/
COPY config.yaml /app/

# Set up symbol library path
ENV SYMBOL_PATH=/app/symbols/NOAKADEXPI
ENV JAVA_OPTS="-Xmx2G -Djava.awt.headless=true"

EXPOSE 8080

# Run the Python wrapper service
CMD ["python3", "/app/graphicbuilder-service.py"]