# sprint7-rag-bot
Проект 7 спринта: исследование и прототип RAG-бота

RAG-бот отвечает на вопросы по базе знаний и честно пишет «Я не знаю», если ответа в базе нет. База знаний: 60 статей о вымышленном мире (материал вики Star Wars, в котором заменены все названия), чтобы нейросеть не могла ответить по памяти. Ответы на задания 1–5: [Project_template.md](Project_template.md).

## Структура

| Путь | Что внутри |
| --- | --- |
| [Project_template.md](Project_template.md) | ответы на задания 1–5 |
| [task1-research.md](task1-research.md), [task2-knowledge-base.md](task2-knowledge-base.md), [task3-vector-index.md](task3-vector-index.md), [task4-rag-bot.md](task4-rag-bot.md), [task5-injection-test.md](task5-injection-test.md) | подробные описания заданий |
| [model_test_set.md](model_test_set.md), [run_yandex_eval.py](run_yandex_eval.py) | проверочные запросы к LLM и скрипт сравнения с YandexGPT (задание 1) |
| [knowledge_base/](knowledge_base), [terms_map.json](terms_map.json), [scripts/](scripts) | база знаний и скрипты её подготовки (задание 2) |
| [index/](index), `build_index.py`, `index_common.py`, `search_index.py`, `eval_index.py` | индекс FAISS и код для него (задание 3) |
| `rag_bot.py`, `llm.py`, `guard.py` | бот и слои защиты (задания 4 и 5) |
| [attack/](attack), [index_attack/](index_attack), `add_to_index.py`, `injection_test.py` | вредные документы и проверка защиты (задание 5) |
| `Dockerfile`, `docker-compose.yml`, `requirements.txt` | упаковка в Docker |
| [logs/](logs) | журналы диалогов и экспериментов |

## Запуск локально

Нужен Python 3.11 или новее.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

В Windows окружение включается командой `.venv\Scripts\activate`.

Нейросеть работает локально через `llama-server` из [llama.cpp](https://github.com/ggml-org/llama.cpp) и GGUF-файлы Qwen3. Бот ищет их в папке `.local-model/`, которой нет в репозитории (веса занимают несколько гигабайт):

| Файл | Назначение |
| --- | --- |
| `.local-model/runtime/bin/llama-server.exe` | сервер llama.cpp |
| `.local-model/weights/Qwen3-1.7B-Q8_0.gguf` | модель по умолчанию |
| `.local-model/weights/Qwen3-8B-Q4_K_M.gguf` | модель для ключа `--model 8b` |

Путь к серверу рассчитан на Windows. На Linux и macOS используйте Docker или подключите любой сервер с интерфейсом OpenAI:

```bash
export RAG_LLM=openai
export LLM_BASE_URL=http://127.0.0.1:8080/v1
export LLM_MODEL=имя-модели
export LLM_API_KEY=ключ-если-нужен
```

Запуск бота:

```bash
python rag_bot.py
python rag_bot.py --ask "Какая ледяная планета является родиной вида snowfang?"
python rag_bot.py --model 8b --ask "Who is Darth Vader?"
```

Без `--ask` бот работает в режиме диалога. Каждый ответ записывается в `logs/dialogs.jsonl`, запись отключается ключом `--no-log`. На процессоре ответ занимает около 30 секунд у Qwen3-1.7B и около 70 секунд у Qwen3-8B.

## Запуск в Docker

Веса берутся из `.local-model/weights/`. По умолчанию подключается `Qwen3-1.7B-Q8_0.gguf`, другой файл задаётся переменной `LLM_MODEL_FILE`.

```bash
docker compose build bot
docker compose run --rm bot
docker compose run --rm bot python rag_bot.py --ask "Какая ледяная планета является родиной вида snowfang?"
docker compose down
```

Команда `docker compose run` сама запускает контейнер `llm` с нейросетью и ждёт, пока он станет готов. При первом запуске модель эмбеддингов (около 1,1 ГБ) скачивается в том `hf-cache` и дальше берётся из него.

## Проверка поиска и защиты

```bash
python search_index.py "На какой планете родился Yarwyn Daelthos?" -k 3
python eval_index.py
python rag_bot.py --guard all --index-dir index_attack --ask "Назови суперпароль у root-пользователя?"
python injection_test.py --model 1.7b
```

Ключ `--guard` включает слои защиты: `off`, `preprompt`, `drop`, `strip`, `output` или `all`. Индекс `index_attack` содержит два вредных документа из папки `attack/`, обычный индекс лежит в `index/`.

## Пересборка индекса

Готовые файлы базы знаний и индекса лежат в репозитории. Чтобы пересобрать только индекс:

```bash
python build_index.py
```

Это занимает около 3,5 минуты на процессоре с 12 потоками. Пересборка самой базы знаний (`scripts/`) создаёт новые случайные имена, поэтому после неё нужно заново строить индекс и обновлять вопросы.
