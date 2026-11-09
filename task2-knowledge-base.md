# Задание 2. Подготовка базы знаний

## Что получилось

| Что | Результат |
|---|---|
| Папка `knowledge_base/` | **60 документов** в формате Markdown, один файл на одну сущность, всего около 82 тысяч слов (от 480 до 1500 слов в документе) |
| `terms_map.json` | словарь замен «исходное → вымышленное», **1715 записей** |
| Скрипты | `scripts/fetch_pages.py` (скачивание и очистка), `scripts/manual_terms.py` (ручной словарь), `scripts/make_generic_words.py` и `scripts/build_knowledge_base.py` (замена терминов и проверка) |
| Вселенная | Star Wars, сайт [starwars.fandom.com](https://starwars.fandom.com/) |

## Зачем всё это нужно

RAG-бот должен отвечать по нашей базе знаний, а не «вспоминать» ответ. Если загрузить обычную статью про Дарта Вейдера, нейросеть ответит по памяти: она эту вселенную читала при обучении. Тогда по ответам нельзя понять, работает ли поиск по нашему индексу.

Поэтому в тексте заменены все названия: герои, планеты, техника, организации, вселенная. Для нейросети это новый корпоративный мир, о котором она ничего не знает. Если бот правильно ответит на вопрос про «Ursera Garvash», значит, ответ пришёл из индекса.

## Какие страницы взяты

60 страниц по четырём темам:

| Тема | Количество | Примеры |
|---|---|---|
| Персонажи | 24 | Anakin Skywalker (он же Darth Vader), Luke Skywalker, Yoda, Palpatine, Chewbacca |
| Планеты | 15 | Tatooine, Alderaan, Hoth, Coruscant, Kamino |
| Техника и технологии | 10 | боевая станция DS-1, корабль Millennium Falcon, световой меч, гиперпривод |
| Организации и события | 11 | Galactic Empire, Jedi, Sith, Clone Wars, Battle of Yavin, Order 66 |

## Как это сделано

**Шаг 1. Скачивание и очистка** (`fetch_pages.py`)

- Страницы запрашиваются через API вики (MediaWiki, действие `parse`) с паузой 1,2 секунды между запросами, чтобы не нагружать сайт.
- Из HTML оставлены только абзацы, заголовки и списки. Таблицы, карточки-справки, сноски `[1]`, навигация и подписи к картинкам выброшены.
- Разделы, которых нет в сюжете вселенной (`Behind the scenes`, `Appearances`, `Sources`, `Notes and references`), отрезаны: в них упоминаются реальные фильмы и актёры.
- Длинные статьи обрезаны примерно до 1500 слов по границе абзаца.

**Шаг 2. Словарь замен.** Он собирается из двух частей:

1. **Ручной** (`manual_terms.py`, около 160 записей). Ключевые понятия, которые нужно заменить осмысленно:
   - названия вселенной и организаций: `Galactic Empire` → `Vastrian Dominion`, `Clone Wars` → `Echo Wars`;
   - технологии: `lightsaber` → `plasmablade`, `blaster` → `pulser`, `droid` → `automaton`;
   - выдуманные существа и материалы: `tauntaun` → `snowstrider`, `carbonite` → `stasisium`.
2. **Автоматический.** Скрипт находит в текстах все слова с заглавной буквы, которые не похожи на обычные английские слова (для этого используется частотный словарь `wordfreq`), и придумывает каждому имя из случайных слогов. Генератор работает с фиксированным seed, поэтому результат повторяется при каждом запуске.

**Как сохранена логика мира:**

- Замена идёт по отдельным словам. `Skywalker` везде превращается в `Daelthos`, значит `Luke Skywalker` и `Anakin Skywalker` получили общую фамилию, как в оригинале.
- Притяжательные формы и множественное число переносятся автоматически: `Skywalker's` → `Daelthos's`.
- Названия жителей строятся от названия планеты: `Geonosis` → `Quinria`, `Geonosian` → `Quinrian`.
- Обычные слова вроде `Battle`, `Council`, `Order`, `Temple` не заменяются, иначе текст перестал бы читаться.
- Один и тот же персонаж с двумя именами получил два разных: `Anakin Skywalker` → `Yarwyn Daelthos`, `Darth Vader` → `Ursera Garvash`. Как и в оригинале, в тексте есть «его второе имя».

**Шаг 3. Замена** (`build_knowledge_base.py`). Все замены выполняются за один проход регулярным выражением, самые длинные совпадения проверяются первыми (`Galactic Empire` раньше, чем `Empire`). Файл называется по новому заголовку, поэтому по имени файла исходное название не угадать (например, `yarwyn-breethmund.md`).

**Шаг 4. Проверка утечек.** Скрипт ищет в готовых текстах около 150 слов, которые выдают вселенную. Из исходных имён в текстах не осталось ни одного. Намеренно оставлены обычные английские слова `clone`, `rebel`, `senate`: сами по себе они не позволяют узнать вселенную.

## Примеры замен

| Было | Стало |
|---|---|
| Anakin Skywalker | Yarwyn Daelthos |
| Darth Vader | Ursera Garvash |
| Luke Skywalker | Havrgan Daelthos |
| Tatooine | Tevlan |
| Death Star | Void Core |
| the Force | the Synth Flux |
| Jedi | Salphos |
| Sith | Zargoth |
| lightsaber | plasmablade |
| Galactic Empire | Vastrian Dominion |
| Clone Wars | Echo Wars |
| Order 66 | Edict 41 |
| R2-D2 | T2-W2 |
| 41 BBY | 41 BKV |

**Фрагмент до:**

> Anakin Skywalker was a legendary Force-sensitive human male who was a Jedi Knight of the Galactic Republic and the prophesied Chosen One of the Jedi Order, destined to bring balance to the Force. His alter ego, Darth Vader, the Dark Lord of the Sith, was created when Skywalker turned…

**Фрагмент после:**

> Yarwyn Daelthos was a legendary Flux-sensitive human male who was a Salphos Knight of the Concord of Auren and the prophesied Chosen One of the Salphos Order, destined to bring balance to the Synth Flux. His alter ego, Ursera Garvash, the Dark Lord of the Zargoth, was created when Daelthos turned…

## Ограничения

- **Сюжет остаётся узнаваемым** для человека, который хорошо знает вселенную. Но модель не сможет «вспомнить» ответ по именам, которых нет в её обучении. Именно это и проверяется в задании 5: вопрос про исходное имя (`Darth Vader`) должен давать «Я не знаю», а про `Ursera Garvash` — ответ из базы.
- Часть общих слов в названиях осталась как есть (`Chosen One`, `Dark Lord`, `Grand Army`). Это не имена, а описательные слова.
- Язык документов — английский (так устроен исходный сайт). Бот в задании 4 отвечает по ним и на русском языке: модель эмбеддингов `multilingual-e5-base` понимает оба языка.
- Скрипт сам находит имена, которые хотя бы раз встречаются внутри предложения. Слова, которые стоят только в начале предложения, он отличить от обычных слов не может. Их список просмотрен вручную, настоящие имена (`Morad`, `Branon`, `Tumperakki` и другие) добавлены в список принудительных замен.

## Источник и лицензия

Тексты взяты с Fandom (Wookieepedia). Содержимое Fandom обычно распространяется по лицензии CC BY-SA, поэтому производные тексты в `knowledge_base/` сохраняют ту же лицензию с указанием источника. Условия: [fandom.com/licensing](https://www.fandom.com/licensing).

## Как воспроизвести

```bash
pip install requests wordfreq
python scripts/fetch_pages.py
python scripts/make_generic_words.py
python scripts/build_knowledge_base.py --report
```

Исходные скачанные тексты (`raw/`, `raw_html/`) в репозиторий не добавляются: они перечислены в `.gitignore`.
