FROM huggingface/transformers-pytorch-gpu

ENV TZ=Asia/Krasnoyarsk
ENV DEBIAN_FRONTEND=noninteractive  

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    apt-get update && apt-get install -y tzdata && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Install all necessary dependencies in a single layer for optimization
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    diffusers \
    accelerate \
    transformers \
    pillow \
    python-dotenv \
    fastapi \
    uvicorn[standard] \
    pydantic

CMD ["/bin/bash"]
