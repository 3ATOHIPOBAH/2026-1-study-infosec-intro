# Шаблон академического отчёта

Основа: [yamadharma/academic-laboratory-report-template, каталог report](https://github.com/yamadharma/academic-laboratory-report-template/tree/master/report).

Используются структура разделов исходного шаблона, формат A4, основной размер PDF 12 pt, полуторный интервал, класс scrreprt, оглавление, списки рисунков и таблиц, числовые ссылки и стиль ГОСТ Р 7.0.5–2008.

Исходные настройки сохранены в upstream-quarto.yml. Для сборки настроен XeLaTeX; библиография обрабатывается citeproc с исходным CSL. При отсутствии IBM Plex и Libertine используются заданные в настройках DejaVu. DOCX использует отдельный файл стилей с теми же параметрами бумаги и основного текста.

Для сборки отчётов из Markdown:

    python3 releases/reformat_reports.py --prepare
    python3 releases/reformat_reports.py --quarto /path/to/quarto
    python3 releases/reformat_reports.py --package

Подготовка сохраняет имеющиеся экспериментальные результаты и скриншоты. Расчётные матрицы прав ЛР2 и ЛР3 размещены в приложениях.
