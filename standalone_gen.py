import os
import json
import random
import uuid
import urllib.request
from websocket import create_connection 

SERVER_ADDRESS = "comfyui:8188"
WORKFLOW_PATH = "workflows/pony_base_api.json"

def parse_random_tags() -> str:
    """Выбирает случайные параметры из блоков конфигурации (разделитель строго ';')"""
    actions = [a.strip() for a in os.getenv("RANDOM_ACTIONS", "").split(";") if a.strip()]
    skin = [s.strip() for s in os.getenv("RANDOM_SKIN_DETAILS", "").split(";") if s.strip()]
    camera = [c.strip() for c in os.getenv("RANDOM_CAMERA_ANGLES", "").split(";") if c.strip()]
    lighting = [l.strip() for l in os.getenv("RANDOM_LIGHTING", "").split(";") if l.strip()]
    env = [e.strip() for e in os.getenv("RANDOM_ENVIRONMENT", "").split(";") if e.strip()]

    chosen = [
        random.choice(actions) if actions else "",
        random.choice(skin) if skin else "",
        random.choice(camera) if camera else "",
        random.choice(lighting) if lighting else "",
        random.choice(env) if env else ""
    ]
    return ", ".join([tag for tag in chosen if tag])

def main():
    client_id = str(uuid.uuid4())
    print(f"🤖 Инициализация клиента оркестратора [{client_id}]...")
    
    # Загружаем базовые стартеры качества
    positive_starter = os.getenv("IMAGE_POSITIVE_STARTER", "score_9, score_8_up, score_7_up")
    negative_starter = os.getenv("IMAGE_NEGATIVE_STARTER", "score_4, score_5, score_6")
    
    # Монолитная строка персонажа
    character_tags = os.getenv("RANDOM_BASE_CHARACTER_TAGS", "")
    dynamic_actions = parse_random_tags()
    
    final_positive = f"{positive_starter}, {character_tags}"
    if dynamic_actions:
        final_positive += f", {dynamic_actions}"
    final_negative = negative_starter
    generation_seed = random.randint(0, 2**32 - 1)

    # Жестко выводим в логи ВСЁ, что отправляем в ComfyUI
    print(f"🔥 [Боевой позитивный промпт]:\n{final_positive}\n")
    print(f"💀 [Боевой негативный промпт]:\n{final_negative}\n")
    print(f"🎲 [Семя генерации (Seed)]: {generation_seed}\n")

    with open(WORKFLOW_PATH, 'r', encoding='utf-8') as f:
        prompt_graph = json.load(f)

    # 🛠️ ПРОВЕРКА И ИНЖЕКТ В ДЕФОЛТНЫЙ DIFFUSERS-ГРАФ
    # Нода 6 - Positive, Нода 7 - Negative, Нода 3 - KSampler
    prompt_graph["6"]["inputs"]["text"] = final_positive
    prompt_graph["7"]["inputs"]["text"] = final_negative
    prompt_graph["3"]["inputs"]["seed"] = generation_seed

    # Открываем вебсокет-соединение
    ws_url = f"ws://{SERVER_ADDRESS}/ws?clientId={client_id}"
    print("🔌 Установка WebSocket соединения с генератором...")
    ws = create_connection(ws_url)
    
    print("🚀 Запуск инференса Pony V7 на RTX 4080...")
    res = queue_prompt(prompt_graph, client_id)
    prompt_id = res['prompt_id']
    print(f"🎯 Задача добавлена! ID: {prompt_id}. Ожидание шагов рендеринга...\n")

    # Перехватываем стриминг шагов рендеринга
    while True:
        try:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                msg_type = message.get('type')
                
                # Исправлено: парсинг прогресса шагов KSampler
                if msg_type == 'progress':
                    data = message.get('data', {})
                    print(f"⏳ Прогресс рендеринга: {data.get('value')}/{data.get('max')} шагов.")
                    
                # Отслеживание полного финиша генерации
                if msg_type == 'executing':
                    data = message.get('data', {})
                    if data.get('node') is None and data.get('prompt_id') == prompt_id:
                        print("\n✅ Рендеринг и VAE Decode успешно завершены!")
                        break
            else:
                continue
        except KeyboardInterrupt:
            print("🛑 Остановка прослушивания очереди.")
            break

    ws.close()
    print("📁 Выполнение полностью завершено. Проверяй outputs/ image.")

def queue_prompt(prompt_graph: dict, client_id: str):
    p = {"prompt": prompt_graph, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{SERVER_ADDRESS}/prompt", data=data)
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))

if __name__ == "__main__":
    main()
