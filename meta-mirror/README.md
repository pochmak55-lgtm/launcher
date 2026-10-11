# meta-mirror — зеркало меты Liquid Launcher

## Зачем
Лаунчер берёт **список** версий из маленькой меты, а **гигабайты игры** —
всегда напрямую с Mojang (клиент редистрибьютить нельзя). Чужим
`meta.prismlauncher.org` в проде не пользуемся (чужой bandwidth без SLA),
поэтому держим своё зеркало в репо `launcher/` рядом с
`server.json`/`news.json`:

```
launcher/
  server.json  news.json  visuals.json   # как было
  meta/
    v1/
      net.minecraft/index.json
      net.minecraftforge/index.json
      net.neoforged/index.json
      net.fabricmc.fabric-loader/index.json
      org.quiltmc.quilt-loader/index.json
      mojang-manifest.json               # id → url JSON версии (Mojang)
      java.json                          # свежие Temurin JRE
```

Лаунчер читает по очереди (первая живая wins):
1. `https://raw.githubusercontent.com/pochmak55-lgtm/launcher/main/meta/v1/...`
2. `https://cdn.jsdelivr.net/gh/pochmak55-lgtm/launcher@main/meta/v1/...`
3. `https://meta.prismlauncher.org/v1/...` (аварийный фолбэк)

Формат Prism-индексов **не меняем** — парсер в `lib/services/launcher_api.dart`
(`_parsePrismIndex`) ест их как есть.

## Файлы
- `generate.py` — генератор (только stdlib). Копирует 5 Prism-индексов
  как есть, кладёт Mojang-манифест, собирает `java.json` из Adoptium API
  (мажоры 8/17/21 × windows/linux/mac × x64/aarch64).
- `refresh-meta.yml` — GitHub Actions: cron раз в сутки + ручной запуск.
  **Положить в репо как `.github/workflows/refresh-meta.yml`.**
  Отдельного токена не надо (хватает `GITHUB_TOKEN`).

## Деплой (первый раз)
```bash
# в корне репо launcher/:
cp -r <этот_каталог> meta-mirror
mkdir -p .github/workflows
cp meta-mirror/refresh-meta.yml .github/workflows/refresh-meta.yml
python3 meta-mirror/generate.py --out meta
git add meta meta-mirror .github/workflows/refresh-meta.yml
git commit -m 'meta: liquid mirror'
git push
# дальше Actions обновляет meta/v1 сам раз в сутки
```

Проверка после пуша:
- `.../main/meta/v1/net.minecraft/index.json` отдаёт JSON (raw),
- то же через jsDelivr (кеш до суток — для свежих файлов ждать/пуржить).

## java.json
```json
{ "generated": "…", "runtimes": [
  { "major": 17, "platforms": {
    "windows-x64": { "release": "…", "url": "…", "sha256": "…", "size": 0 }
  }}]}
```
Самому запуску игры он не нужен (инсталлер качает JRE по стабильному
редиректу `api.adoptium.net/v3/binary/latest/…`), файл — для будущего UI
«обновить Java» и для прозрачности.
