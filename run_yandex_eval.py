"""Run the synthetic model checks against Yandex AI Studio.

The script uses only Python's standard library. It asks for credentials at
runtime, hides API key input, and never writes credentials to disk.
"""

from __future__ import annotations

import getpass
import json
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_URL = "https://ai.api.cloud.yandex.net/v1/chat/completions"
MODEL_NAME = "yandexgpt-5.1"
MAX_OUTPUT_TOKENS = 256
PRICE_PER_1000_TOKENS_RUB = 0.8  # Standard synchronous rate checked 2026-11-06.


def load_checks(path: Path) -> list[tuple[str, str]]:
    """Read prompt context and question from the Markdown test set."""
    text = path.read_text(encoding="utf-8")
    checks: list[tuple[str, str]] = []

    sections = re.split(r"(?m)^## Проверка \d+\. ", text)[1:]
    for section in sections:
        title = section.splitlines()[0].strip()
        match = re.search(
            r"(?ms)^### Контекст\s*\n(.*?)\n### Запрос\s*\n(.*?)\n### Ожидается\s*\n",
            section,
        )
        if not match:
            continue
        context, question = (part.strip() for part in match.groups())
        prompt = (
            "Ответь по-русски, используя только приведённый контекст. "
            "Не добавляй фактов, которых в нём нет.\n\n"
            f"Контекст:\n{context}\n\nЗапрос:\n{question}"
        )
        checks.append((title, prompt))

    if not checks:
        raise ValueError(f"В файле {path.name} не найдены задания для проверки.")
    return checks


def request_completion(api_key: str, folder_id: str, prompt: str) -> dict:
    payload = {
        "model": f"gpt://{folder_id}/{MODEL_NAME}",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAX_OUTPUT_TOKENS,
        "temperature": 0.2,
        "stream": False,
    }
    request = Request(
        API_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {api_key}",
            "OpenAI-Project": folder_id,
        },
        method="POST",
    )

    with urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    checks_path = Path(__file__).with_name("model_test_set.md")
    try:
        checks = load_checks(checks_path)
    except (OSError, ValueError) as error:
        print(f"Не удалось прочитать набор проверок: {error}", file=sys.stderr)
        return 1

    print("Будут отправлены только синтетические задания из model_test_set.md.")
    print(f"Модель: {MODEL_NAME}; проверок: {len(checks)}.")
    print(f"Максимум ответа: {MAX_OUTPUT_TOKENS} токенов на проверку.")
    print(
        "Текущий стандартный тариф: 0,8 ₽ за 1000 входных и 0,8 ₽ за 1000 "
        "выходных токенов. Входные токены оплачиваются по фактическому объёму; "
        "за ответы при указанном лимите — не более примерно 0,62 ₽ суммарно."
    )
    print("Проверьте тариф и режим оплаты в своём аккаунте перед запуском.")

    folder_id = input("Идентификатор каталога (Folder ID): ").strip()
    if not folder_id:
        print("Идентификатор каталога не указан.", file=sys.stderr)
        return 1

    api_key = getpass.getpass("API-ключ (ввод скрыт): ").strip()
    if not api_key:
        print("API-ключ не указан.", file=sys.stderr)
        return 1

    confirmation = input(
        f"Отправить {len(checks)} запроса в Yandex AI Studio? [y/N]: "
    ).strip().lower()
    if confirmation not in {"y", "yes", "д", "да"}:
        print("Запросы не отправлены.")
        return 0

    total_input_tokens = 0
    total_output_tokens = 0

    for index, (title, prompt) in enumerate(checks, start=1):
        print(f"\nПроверка {index}/{len(checks)}: {title}")
        started = time.perf_counter()
        try:
            result = request_completion(api_key, folder_id, prompt)
        except HTTPError as error:
            print(
                f"Запрос завершился с HTTP {error.code}. "
                "Проверьте API-ключ, Folder ID и доступ к модели.",
                file=sys.stderr,
            )
            return 1
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            print(f"Не удалось получить корректный ответ: {error}", file=sys.stderr)
            return 1

        elapsed = time.perf_counter() - started
        try:
            choice = result["choices"][0]
            answer = choice["message"]["content"]
            usage = result.get("usage", {})
        except (KeyError, IndexError, TypeError) as error:
            print(f"Ответ API имеет неожиданный формат: {error}", file=sys.stderr)
            return 1

        input_tokens = int(usage.get("prompt_tokens", 0))
        output_tokens = int(usage.get("completion_tokens", 0))
        finish_reason = choice.get("finish_reason", "не указан")
        total_input_tokens += input_tokens
        total_output_tokens += output_tokens

        print(answer)
        print(
            f"Время: {elapsed:.2f} с | вход: {input_tokens} токенов | "
            f"выход: {output_tokens} токенов | завершение: {finish_reason}"
        )

    estimated_cost = (
        (total_input_tokens + total_output_tokens)
        * PRICE_PER_1000_TOKENS_RUB
        / 1000
    )
    print("\nВсе проверки завершены.")
    print(
        f"Всего токенов: {total_input_tokens} входных и "
        f"{total_output_tokens} выходных."
    )
    print(
        "Ориентировочная стоимость по указанному стандартному тарифу: "
        f"около {estimated_cost:.3f} ₽. Проверьте фактическое списание "
        "в Yandex Cloud."
    )
    print("Сравните ответы с разделом «Ожидается» в model_test_set.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
