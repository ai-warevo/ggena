FROM huggingface/transformers-pytorch-gpu
WORKDIR /workspace

COPY . /workspace

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir diffusers accelerate transformers pillow python-dotenv

CMD ["/bin/bash"]
