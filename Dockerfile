# Используем официальный образ от Hugging Face как базу
FROM huggingface/transformers-pytorch-gpu

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /workspace

# Копируем файлы проекта (для продакшена)
COPY . /workspace

# Обновляем pip и устанавливаем необходимые библиотеки для генерации изображений
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir diffusers accelerate transformers pillow python-dotenv

# Указываем, что по умолчанию при запуске будет открываться bash
CMD ["/bin/bash"]
