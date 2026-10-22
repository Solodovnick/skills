---
name: tts
description: Создаёт короткую озвучку видео, локальные русскоязычные аудиокниги и длинные TTS-записи из EPUB, PDF или Markdown с Qwen3-TTS 8-bit либо Silero/Kseniya, батчевой проверкой ударений и словоформ, независимым Whisper ASR-контролем, безопасной сборкой MP3 и опциональной личной загрузкой в Яндекс Музыку. Используется для TTS, аудиокниг, озвучивания EPUB/PDF/Markdown, Qwen3-TTS, Silero, проверки произношения и подготовки MP3.
---

# TTS: аудиокниги и озвучка видео с контролем качества

## Главный принцип

Не называй аудиокнигу финальной, пока каждый выбранный батч не прошёл автоматический контроль. Если пользователь явно просит собрать запись раньше, выпусти отдельную версию с заметной пометкой «не проверено», снимком QC-состояния и собственными хэшами; продолжай ремонт исходных батчей, не подменяя этой версией будущий проверенный мастер. Сохраняй исходники, промежуточные WAV, транскрипты, метрики, причины ремонта и хэши так, чтобы любой шаг можно было возобновить без повторной генерации готовых фрагментов.

Для коротких реплик и видео используй встроенный раздел «Короткая озвучка: произношение, ремонт и проверяемая сборка» ниже. Следующий маршрут предназначен для аудиокниг.

## Маршрут

1. Зафиксируй входной EPUB/PDF/Markdown и рабочий каталог.
2. Извлеки текст подходящим для формата способом: PDF преобразуй в Markdown и визуально проверь страницы; EPUB обходи в порядке чтения и проверяй покрытие XHTML-разделов.
3. Подготовь отдельный TTS-сценарий: убери служебный шум, восстанови заголовки, раздели на главы.
4. Создай словарь произношений и короткий A/B-тест разметки ударений.
5. Разбей текст на батчи по предложениям и абзацам. Практический стартовый предел — 1200 символов.
6. Проведи лексический аудит ударений и неизменности словоформ на тех же финальных границах батчей.
7. Синтезируй батчи локально и возобновляемо.
8. Проверь каждый батч независимым ASR. Ремонтируй только не прошедшие фрагменты.
9. Только после нулевого списка блокирующих ошибок собери финальные главы и мастер. Для явно запрошенной ранней сборки используй отдельный маршрут в [QUALITY_CONTROL.md](QUALITY_CONTROL.md).
10. Полностью декодируй итоговые файлы, проверь длительность, метаданные, размер и SHA-256.
11. Если нужна личная загрузка в Яндекс Музыку, создай отдельные совместимые копии и проверяй результат по готовым воспроизводимым трекам. Для публичной дистрибуции аудиокниги примени skill `music`.

## Рекомендуемый стек для Apple Silicon

- TTS по умолчанию: `mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit` через `mlx-audio`. Если нужен голос Ксении, используй отдельный маршрут [SILERO_KSENIYA.md](SILERO_KSENIYA.md).
- Независимый ASR: `mlx-community/whisper-large-v3-turbo-8bit` через `mlx-whisper`.
- Русские ударения: для Qwen3-TTS RuAccent служит аналитическим слоем; для Silero после короткого A/B-теста допустимы явные `+` перед ударной гласной.
- Сборка и валидация: FFmpeg/FFprobe.
- PDF: MarkItDown для извлечения, Poppler для визуального и структурного контроля.

Модель, голос и версии библиотек включай в ключ кэша. Не подменяй запрошенную 8-bit модель другой квантизацией без согласования.

## Обязательные quality gates

- Исходные словоформы после разметки ударений сохранены.
- Лексическое покрытие ударениями для каждого батча не ниже 0.98 либо исключение явно объяснено.
- Нормализованное ASR-покрытие слов не ниже 0.85.
- ASR-порог выбран по профилю текста, а не один для всего корпуса.
- Нормализация ASR не удаляет и не лемматизирует русские окончания; различия словоформ остаются видимыми.
- Распределение QC-профилей проверено: обычная проза не получила массово мягкий табличный порог из-за переносов строк PDF.
- Все предупреждения проверены и исправлены либо документированно признаны ложными.
- `technical_failures.json` и `asr_blocking_failures.json` пусты.
- Все финальные MP3 полностью декодируются без ошибок.
- Отчёт честно говорит, была ли человеческая слуховая редактура.

Эти условия относятся к **проверенному финальному выпуску**. Запрошенная пользователем ранняя версия сохраняет все найденные замечания в отчёте и не считается прошедшей QC.

## Критический урок Qwen3-TTS

По умолчанию не подавай в Qwen3-TTS русский текст с комбинируемым знаком ударения `U+0301` и не используй `+` как разметку ударения. В проверенном 8-bit пайплайне обе формы резко ухудшили речь; лучший результат дал обычный русский текст без встроенных знаков ударения.

Используй RuAccent для аудита ожидаемых ударений и словоформ. Для сложных терминов применяй неакцентированные фонетические замены: например, `PDLC → пи-ди-эл-си`. При смене модели или голоса сначала повтори короткий A/B-тест.

Этот вывод относится к проверенному маршруту Qwen3-TTS. В Silero синтаксис `+` и SSML поддерживается отдельно; не переноси правила одного движка на другой.

## Батчи и возобновление

- Разрезай в порядке: абзац → предложение → пробел. Не режь слово, сокращение или числовую конструкцию без необходимости.
- Храни для батча: глава, индекс, исходный диапазон, финальный TTS-текст, настройки, ключ кэша, путь к WAV, SHA-256, ASR-транскрипт и QC-решение.
- Пиши промежуточный файл через `.part`, затем атомарно переименовывай.
- При сбое повторный запуск должен пропускать готовые батчи с совпадающим ключом и хэшем.
- При возобновлении длинного прогона сверяй PID с командой, рост счётчика готовых батчей и свежие ошибки. Записанный PID или запущенный наблюдатель QC сами по себе не подтверждают ни работающий синтез, ни завершённую проверку.
- Если MLX сообщает об отсутствии Metal-устройства внутри ограниченной среды, сначала проверь доступ процесса к Apple Silicon. Сохрани кэш готовых батчей и возобнови синтез в разрешённой среде; не записывай такой сбой как ошибку текста или модели.
- Освобождай MLX-память между тяжёлыми стадиями и после исключений.

## Ремонт

Если батч не прошёл ASR:

1. Определи, это реальный пропуск/повтор или ложное расхождение на аббревиатуре, таблице, числе либо URL.
2. Нормализуй ожидаемый и распознанный текст одинаковыми алиасами.
3. Если покрытие всё ещё ниже 0.85, раздели батч на короткие смысловые части и синтезируй заново.
4. Если модель зациклилась на аббревиатуре, замени только проблемное произношение в этом ремонте; не меняй глобально уже прошедшие фрагменты.
5. Повтори ASR и обнови аудиохэш. Не собирай мастер при оставшихся блокирующих ошибках.

## Сборка

- Собирай из проверенных WAV/MP3 через FFmpeg concat-list с безопасным экранированием путей.
- Нормализуй громкость один раз при финальном кодировании; практический ориентир для речи — `-19 LUFS`, `TP=-1.5`, `LRA=9`.
- Для локального мастера практичный профиль: mono, 24 kHz, MP3 128 kbps, ID3v2.3.
- Добавь `title`, `artist`, `album`, комментарий о синтетическом голосе и, если нужно, ID3 CHAP/CTOC.
- Перед присвоением финального имени полностью декодируй временный файл.

## Отчёт

Укажи:

- модель и квантизацию;
- число глав и батчей;
- длительность;
- результаты лексического и ASR-аудита;
- число ремонтов и оставшихся предупреждений;
- профили итоговых файлов;
- SHA-256 мастера;
- `stress_and_intonation_reviewed_by_human: true/false`.

Не называй автоматический ASR человеческим прослушиванием и не гарантируй идеальные ударения или интонацию без слуховой редакции.
Whisper не транскрибирует ударения. Автоматический контур проверяет ожидаемую акцентную разметку, сохранность словоформ и слышимость слов, но фактическое ударение в аудио подтверждает только слуховая проверка либо отдельная модель акустического ударения.

## Дополнительные инструкции

- Подготовка EPUB/PDF и сценария: [SOURCE_PREPARATION.md](SOURCE_PREPARATION.md)
- Подробный QC и проверенные пороги: [QUALITY_CONTROL.md](QUALITY_CONTROL.md)
- Подготовка чисел, ударений и SSML для Silero с голосом Ксении: [SILERO_KSENIYA.md](SILERO_KSENIYA.md)
- Личная загрузка в Яндекс Музыку и совместимые копии: [YANDEX_MUSIC.md](YANDEX_MUSIC.md)
- Результаты и ограничения эталонного прогона: [CASE_STUDY.md](CASE_STUDY.md)
- Настройки по умолчанию: [settings.example.json](settings.example.json)
- Пример словаря произношений: [pronunciation-overrides.example.json](pronunciation-overrides.example.json)
- Проверка готовых файлов: `scripts/validate_audio.sh <каталог-с-mp3>`

## Короткая озвучка: произношение, ремонт и проверяемая сборка

Практические выводы, инструменты и переносимые скрипты для коротких реплик, обучающих роликов и обновления принятой озвучки.

## 1. Что показала практика

| Наблюдение | Как действовать |
| --- | --- |
| Правильная ASR-транскрипция встречалась при неправильном ударении | Проверять слова автоматически, а ударение — слухом или отдельным акустическим методом. Не смешивать результаты |
| Одобренное написание в короткой пробе давало другое произношение в полной фразе | Одобрение привязывать к конкретному WAV и контексту. После регенерации оно не переносится автоматически |
| Именительный и предложный падежи одного названия звучали по-разному | Хранить словоформы отдельно; успех одной формы не разрешает все остальные |
| Регистр, знак ударения и дефис не давали универсального исправления | Делать ограниченный A/B-тест на выбранном движке и голосе; не обещать результат от одной разметки |
| В коротком вопросе единственное число превращалось во множественное | Проверять критичные слова и окончания точно, даже если общий WER низкий |
| Принятая фраза сохраняла нужное произношение при повторном использовании её звука | При нестабильной регенерации вырезать целую фразу из принятой пробы, записать SHA и границы сэмплов, отдельно проверить стык |
| ASR timestamp начинался позже шипящего согласного | Уточнять монтажные границы по сигналу, а не обрезать строго по timestamp |
| Новый вопрос удалось добавить перед прежней инструкцией | Синтезировать минимальный новый фрагмент; сохранять принятые исходные записи |
| Экспорт 24 kHz → 48 kHz не устранял дефекты синтеза | Рассматривать частоту экспорта как совместимость с монтажом, а не повышение исходного качества |
| Нормализация всего ролика меняла хэши обработанных реплик | Различать неизменность raw-речи и неизменность нормализованного WAV |

Эти наблюдения получены на русской речи. Они не доказывают одинаковое поведение
всех моделей и голосов. Полные финальные мастера в исходном прогоне не прошли
человеческую слуховую редактуру: прослушивались отдельные пробы.

## 2. Инструменты и область применения

| Инструмент | Задача | Граница доказательства |
| --- | --- | --- |
| Qwen3-TTS Base через MLX-Audio | Локальный синтез по референсу голоса и его точному тексту | Загруженная модель ещё не означает успешный синтез |
| VoiceDesign | Создать оригинальный синтетический голос, затем использовать принятый референс | Не подменять выбранный пользователем голос новым без его решения |
| Silero | Альтернативный маршрут с собственными правилами `+`/SSML | Проверять лицензию конкретной модели и разрешённую область использования референса |
| RuAccent | Аналитическая копия текста с ожидаемыми ударениями | Не измеряет ударение в готовой аудиозаписи |
| Whisper, включая MLX-реализации | Независимая транскрипция и word timestamps | Проверяет слышимость слов, но не удостоверяет ударения и естественность интонации |
| NumPy + SoundFile | Анализ сигнала, монтаж по сэмплам, WAV | Монтажный код не выбирает фонетически правильную границу вместо редактора |
| FFmpeg + FFprobe | Decode, LUFS/true peak, кодирование, metadata | Decode PASS не доказывает корректность текста |
| SHA-256 + JSON manifest | Происхождение, кэш, приёмка конкретной версии | Записанная строка revision не подтверждает фактическую версию весов |

Проверенный срез окружения: Python 3.11.16, MLX-Audio 0.5.9, MLX 0.32.4,
Transformers 5.19.0, RuAccent 1.5.8.3, SoundFile 0.14.0, NumPy 2.4.6.
Это описание использованной установки, не обещание совместимости и не новый
обязательный lockfile. Сначала использовать исправное существующее окружение.

Для Base с `ref_audio + ref_text` в проверенной реализации MLX-Audio 0.5.9
использовалась ветка ICL без передачи `instruct`; effective repetition penalty
имела нижнюю границу 1.5. Не предлагать instruction prompt как гарантированное
управление ударением в этой ветке. При смене версии проверить реализацию заново.
Официальные точки входа: [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS),
[MLX-Audio](https://github.com/Blaizzy/mlx-audio).

## 3. Контракт текста, голоса и приёмки

Разделять три представления:

- `display_text`: согласованный текст для сценария, субтитров и публикации;
- `engine_text`: адресные фонетические замены для конкретного движка;
- `analysis_text`: копия для лексического аудита ударений.

Замены применять по полным токенам, с явно перечисленными словоформами.
Сохранять исходный диапазон и замену в ledger; проверить обратное восстановление
исходника. Не удалять окончания, не лемматизировать текст ради прохождения QC.

Минимальная запись одной реплики (значения ниже иллюстративные):

```json
{
  "id": "intro",
  "display_text": "Как создать условие?",
  "engine_text": "Как создать условие?",
  "source_text_sha256": "<sha256>",
  "model": {"id": "<model-id>", "revision": "<resolved-commit>", "quantization": "8bit"},
  "voice": {"reference_sha256": "<sha256>", "reference_text": "<exact transcript>", "authorization": "<scope>"},
  "runtime": {"python": "<version>", "mlx_audio": "<version>"},
  "settings": {"seed": 123, "temperature": 0.65, "top_p": 0.9, "repetition_penalty": 1.5},
  "lexicon_sha256": "<sha256>",
  "audio_sha256": "<sha256>",
  "qc": {"raw_asr": "<verbatim>", "normalized_asr": "<separate>", "critical_words_exact": false},
  "listening": {"trial_accepted": false, "accepted_audio_sha256": null, "full_join_reviewed": false, "full_master_reviewed": false}
}
```

Права на референс и согласие на публикацию хранить отдельно от выбора голоса.
Включение в manifest поля `authorization` само по себе не создаёт разрешения.
Явное поручение пользователя на экспорт/публикацию сохраняется при правках:
не запрашивать то же разрешение повторно только из-за новой версии файла.

## 4. Синтез и ограниченный ремонт

1. Зафиксировать принятый текст и голос; извлечь исходный референс, если он
   сохранился, вместо повторного кодирования звука из видео.
2. Проверить версии runtime, фактический model snapshot и короткий synthesis
   smoke test. Сбой доступа к Metal отличать от дефекта модели или текста.
3. Проверить имя, падежи, числа и короткие команды в пробах. Прослушивание одной
   формы не считать приёмкой всех форм, голосов или будущих реплик.
4. Синтезировать реплики отдельно, сохраняя seed, effective settings и raw WAV.
5. При lexical FAIL сделать одну адресную попытку ремонта; если дефект повторяется,
   сменить подход: разделить фразу, использовать принятый звук или предложить
   конкретный слуховой выбор. Не повторять тот же способ неограниченно.
6. При ASR-написании названия латиницей сохранить raw transcript. Допустимый
   spelling alias применять только в ожидаемой позиции и фиксировать замену.
   Такой alias не доказывает правильность окончания, ударения или произношения.
7. При acoustic FAIL заблокировать отвергнутый вариант для дальнейшей сборки.

### Рецепт синтеза

Сохранить следующий блок как `synthesize_one.py`. Нужны MLX-Audio, MLX,
NumPy и SoundFile в рабочем Python на Apple Silicon. `MODEL_DIR` должен быть
уже скачанным и проверенным snapshot выбранной revision; скрипт не скачивает
модель и не выдаёт её путь за доказательство revision.

```python
import os
from pathlib import Path
import numpy as np
import soundfile as sf
import mlx.core as mx
from mlx_audio.tts.utils import load_model

model_dir = Path(os.environ["MODEL_DIR"])
reference = Path(os.environ["REFERENCE_WAV"])
text = Path(os.environ["ENGINE_TEXT_FILE"]).read_text(encoding="utf-8").strip()
ref_text = Path(os.environ["REFERENCE_TEXT_FILE"]).read_text(encoding="utf-8").strip()
out = Path(os.environ["OUTPUT_WAV"])
if not text or not ref_text or out.exists() or out.with_suffix(".part.wav").exists():
    raise ValueError("Empty text or output already exists; choose a new output")
if not model_dir.is_dir() or not reference.is_file():
    raise ValueError("Missing local model or reference")
model = load_model(str(model_dir))
try:
    mx.random.seed(123)
    chunks, rate = [], None
    for result in model.generate(text=text, ref_audio=str(reference), ref_text=ref_text,
                                 lang_code="Russian", temperature=0.65, top_p=0.9,
                                 repetition_penalty=1.5, max_tokens=1200):
        mx.eval(result.audio)
        current_rate = int(result.sample_rate)
        if rate is not None and current_rate != rate:
            raise ValueError("Mixed sample rates")
        rate = current_rate
        chunks.append(np.asarray(result.audio, dtype=np.float32).reshape(-1))
    if not chunks:
        raise ValueError("No audio produced")
    audio = np.concatenate(chunks)
    if not len(audio) or not np.isfinite(audio).all() or np.max(np.abs(audio)) >= 1:
        raise ValueError("Invalid or clipping waveform")
    part = out.with_suffix(".part.wav")
    sf.write(part, audio, rate, subtype="PCM_24")
    part.rename(out)
finally:
    del model
    mx.clear_cache()
```

Это адаптация использованного API, не универсальная обёртка: перед запуском
на другой версии проверить сигнатуру `generate` и `sample_rate` результата.
Достижение token cap, обрыв фразы и повтор слов проверяются последующим QC.
Зафиксировать параметры и SHA результата в manifest; одинаковый seed не обещает
побайтовой воспроизводимости между версиями runtime.

## 5. Переносимый помощник проверки и склейки

Сохранить блок как `audio_tools.py`. Требуются NumPy, SoundFile, FFmpeg/FFprobe
в `PATH`. Это новая обобщённая реализация проверенных приёмов: её smoke-тесты
на синтетических сигналах проверяют механику, но не заменяют слуховой проверки.
Исходники не перезаписываются; выходной каталог должен существовать.

```python
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
import numpy as np
import soundfile as sf

def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def cache_key(contract):
    raw = json.dumps(contract, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def run(args):
    return subprocess.run(args, check=True, capture_output=True, text=True)

def inspect(path):
    path = str(Path(path).resolve())
    metadata = json.loads(run(["ffprobe", "-v", "error", "-show_streams",
                               "-show_format", "-of", "json", path]).stdout)
    if not any(s.get("codec_type") == "audio" for s in metadata["streams"]):
        raise ValueError("No audio stream")
    run(["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-i", path,
         "-map", "0:a:0", "-f", "null", "-"])
    return {"sha256": digest(path), "bytes": Path(path).stat().st_size,
            "decode": "PASS", "metadata": metadata,
            "full_master_reviewed_by_human": False}

def splice(a):
    out = Path(a.output).resolve()
    part = out.with_suffix(".part.wav")
    receipt = out.with_suffix(out.suffix + ".json")
    if out.suffix.lower() != ".wav":
        raise ValueError("Output must be WAV")
    if any(p.exists() for p in (out, part, receipt)):
        raise ValueError("Output/temporary file/receipt already exists")
    left, sr = sf.read(a.prefix, dtype="float64", always_2d=True)
    right, rr = sf.read(a.accepted, dtype="float64", always_2d=True)
    if sr != rr or left.shape[1] != right.shape[1]:
        raise ValueError("Explicitly convert sample rate/channels before splice")
    if not (0 < a.prefix_end <= len(left) and 0 <= a.start < a.end <= len(right)):
        raise ValueError("Sample bounds outside source")
    if not all(np.isfinite(v).all() for v in (left, right)):
        raise ValueError("Non-finite source")
    if not np.isfinite(a.gain) or a.gain <= 0 or a.gap_ms < 0 or a.fade_ms < 0:
        raise ValueError("Invalid gain/gap/fade")
    prefix = left[:a.prefix_end].copy()
    phrase = right[a.start:a.end].copy() * a.gain
    fade = round(sr * a.fade_ms / 1000)
    gap = round(sr * a.gap_ms / 1000)
    if fade >= min(len(prefix), len(phrase)):
        raise ValueError("Fade consumes phrase")
    # Separate fades around an explicit gap, not an overlap/crossfade.
    if fade:
        prefix[-fade:] *= np.linspace(1, 0, fade)[:, None]
        phrase[:fade] *= np.linspace(0, 1, fade)[:, None]
    joined = np.concatenate((prefix, np.zeros((gap, left.shape[1])), phrase))
    if not np.isfinite(joined).all() or np.max(np.abs(joined)) >= 1:
        raise ValueError("Non-finite or clipping output; choose a lower gain")
    ledger = {"prefix_sha256": digest(a.prefix), "accepted_sha256": digest(a.accepted),
              "prefix_end_sample": a.prefix_end, "accepted_start_sample": a.start,
              "accepted_end_sample_exclusive": a.end, "sample_rate": sr,
              "gain": a.gain, "gap_samples": gap, "fade_samples": fade,
              "new_synthesis": False, "human_full_join_reviewed": False}
    try:
        sf.write(part, joined, sr, subtype="PCM_24")
        report = inspect(part)
        part.rename(out)
        receipt.write_text(json.dumps({**report, "splice": ledger},
                                      ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    finally:
        part.unlink(missing_ok=True)
    return {"output": str(out), "sha256": digest(out), "splice": ledger}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    qc = commands.add_parser("inspect")
    qc.add_argument("file")
    edit = commands.add_parser("splice")
    for name in ("prefix", "accepted", "output"):
        edit.add_argument("--" + name, required=True)
    for name in ("prefix-end", "start", "end"):
        edit.add_argument("--" + name, type=int, required=True)
    edit.add_argument("--gain", type=float, default=1.0)
    edit.add_argument("--gap-ms", type=float, default=80)
    edit.add_argument("--fade-ms", type=float, default=3)
    args = parser.parse_args()
    result = inspect(args.file) if args.command == "inspect" else splice(args)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
```

Пример вызова; границы ниже иллюстративные, их надо определить для своих файлов:

```bash
python audio_tools.py inspect source.wav > source.qc.json
python audio_tools.py splice --prefix source.wav --accepted accepted.wav \
  --prefix-end 120000 --start 48000 --end 96000 \
  --gain 0.8 --gap-ms 80 --fade-ms 3 --output repaired.wav
```

Скрипт не устанавливает факт человеческой приёмки `accepted.wav` — до вызова
сверить SHA с записью приёмки. Не выбирать границы или gain вслепую. Небольшой
fade может убрать щелчок, но также съесть согласный при неверной границе.
Для RMS matching нужны явно выбранные речевые окна, проверка на пустоту,
тишину и конечность делителя; автоматический gain по всей записи не применяется.
Если нужен resampling, сделать отдельную копию и записать её происхождение:

```bash
ffmpeg -nostdin -n -i accepted.wav -ar 24000 -ac 1 -c:a pcm_s24le accepted-24k.wav
```

## 6. Громкость, мастер и кэш

Сначала выбрать голос и исправить произношение. EQ, компрессия и увеличение
sample rate не заменяют этот этап. Для короткой озвучки ролика в проверенном
случае использовался ориентир около −17 LUFS и true peak не выше −1.5 dBTP;
для аудиокниги основной навык предлагает другой профиль. Цель выбирать по
назначению и измеренному референсу, не превращать один пример в универсальный стандарт.

Измерить исходник первым проходом:

```bash
ffmpeg -nostdin -hide_banner -i assembled.wav \
  -af 'loudnorm=I=-17:TP=-1.5:LRA=7:print_format=json' -f null - 2> loudness.log
```

Второй проход использует `input_i`, `input_tp`, `input_lra`, `input_thresh`
и `target_offset` из JSON первого прохода как `measured_I`, `measured_TP`,
`measured_LRA`, `measured_thresh`, `offset`. Проверить конечность значений:
тишина может дать `-inf`. Пример параметров фильтра, не готовые измерения:

```text
loudnorm=I=-17:TP=-1.5:LRA=7:measured_I=<input_i>:measured_TP=<input_tp>:measured_LRA=<input_lra>:measured_thresh=<input_thresh>:offset=<target_offset>:linear=true
```

FFmpeg может перейти к dynamic normalization; прочитать отчёт, затем измерить
готовый WAV и финальный lossy-файл. True peak после MP3/AAC может измениться.
Один проход мастеринга относится к одному законченному ролику. При ремонте
собирать заново из raw-фрагментов, а не повторно обрабатывать прошлый мастер.
Для видео можно нарезать обработанный мастер обратно на сцены по точным
сэмплам; это сохранит общую громкость и рассчитанные паузы.

Наличие файла и совпадение длительности не доказывают пригодность кэша.
Использовать `cache_key()` из помощника с полным контрактом стадии:

| Стадия | Что включать в ключ |
| --- | --- |
| TTS | display/engine text, lexicon hash, model snapshot, runtime, reference audio/text, effective settings, seed |
| ASR | audio SHA, expected text, ASR model/revision/settings, normalizer version, aliases/lexicon hash |
| Assembly | упорядоченные input SHA, sample ranges, gaps/fades/gains, FFmpeg version, filter graph и encoder settings |

Рядом хранить output SHA и проверять его перед reuse. Смена текста той же
длины, alias, модели ASR или принятого аудиофрагмента должна инвалидировать
соответствующий кэш. Стадии не должны переписывать исходники и прежние версии.

## 7. Что переносить из рабочих скриптов

Это карта происхождения приёмов, **не список дополнительных файлов пакета**.
Исходные имена приведены для понимания ролей; сами task-specific скрипты не
распространяются и не нужны для применения рецептов выше.

| Роль в рабочем пайплайне | Обобщённый контракт |
| --- | --- |
| `pronunciation.py`, `stress_audit.py` | display/engine/analysis, guards по голосу и словоформе, обратимый ledger |
| `voice_a_production.py`, `question05_synthesis.py` | принятый reference, bounded synthesis, независимые сцены; см. рецепт синтеза |
| `voice_a_asr.py`, `asr_audit.py` | raw и normalized ASR раздельно, точные критичные слова, scoped spelling aliases |
| `accepted_phrase_timestamps.py`, `splice_accepted_scene03.py` | границы по ASR + сигналу, перенос actual waveform; см. `splice` |
| `join_question05.py`, `assemble_split.py` | минимальный ремонт и общий mastering каждого самостоятельного ролика |
| receipts и `scripts/validate_audio.sh` | decode, metadata, SHA, честное состояние слуховой приёмки |

При статическом аудите исходных прототипов найдены: абсолютные пути, старые
literal SHA сценария, reuse мастера по наличию файлов, неполный ASR cache key,
неприкреплённая download revision, устаревший тест словаря и повторная запись
backup с фиксированным именем. Исторический отчёт о проходе тестов не доказывает,
что текущий скрипт проходит их сейчас. Эти прототипы нельзя выдавать за переносимый
production CLI. В новых помощниках использовать явные исключения вместо `assert`
для входных проверок: `python -O` отключает assert.

## 8. Передача в видео и публикация

- Тайминги и word cues брать из окончательного аудио; title/instruction переключать
  вместе с соответствующими словами. Проверить кадры до и после перехода.
- Сквозные действия одного флоу нумеровать последовательно, даже при смене сцены.
- Проверять фактически экспортированный MP4, а не только Studio preview.
- После разрешённой загрузки сверить удалённый файл с локальным по SHA, размеру,
  MIME и воспроизведению. Публиковать стабильную ссылку, а не подписанный URL.
- При обновлении комментария перечитать текущий текст, сохранить чужие правки,
  заменить нужную ссылку/реплику и проверить readback. Не создавать дубли.
- Раздельно сообщать: lexical QC, decode, acoustic trial acceptance, full join
  listening и full master listening. Ни один из этих статусов не заменяет остальные.

При проверке этого справочника были выполнены механические smoke-тесты помощника
на синтетических WAV: decode, корректный монтаж, отклонение неверных диапазонов,
несовместимых sample rates, clipping и существующего выхода; проверена инвалидация
ключа при смене входного SHA. Рецепт MLX проверен синтаксически и по локальному
API; новый синтез для самого PR не выполнялся. Естественность стыков требует
проверки на конкретной речи.
