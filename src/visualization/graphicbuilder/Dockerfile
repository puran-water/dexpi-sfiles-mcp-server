# GraphicBuilder Docker Image
# Production DEXPI P&ID renderer microservice
# Using Java 8 (GraphicBuilder requires Java 8 due to JAXB dependencies)
FROM eclipse-temurin:8-jdk-jammy

# GraphicBuilder version (can be overridden with --build-arg)
# Using master branch as tags are not Java 17 compatible
# To use a different version: docker build --build-arg GB_REF=refs/heads/some-branch .
ARG GB_REF=master

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

# Clone and build GraphicBuilder (pinned to specific version)
# Repository: https://gitlab.com/dexpi/GraphicBuilder
RUN git clone https://gitlab.com/dexpi/GraphicBuilder.git && \
    cd GraphicBuilder && \
    git checkout ${GB_REF} && \
    echo "=== GraphicBuilder Build Info ===" && \
    echo "Version: ${GB_REF}" && \
    git log -1 --pretty=format:"Commit: %H%nDate: %ai%nAuthor: %an%n" && \
    echo "=== License Information ===" && \
    cat LICENSE 2>/dev/null || echo "No LICENSE file found" && \
    echo "================================" && \
    cd org.dexpi.pid.xml && \
    mvn clean install -DskipTests && \
    cd ../org.dexpi.pid.imaging && \
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