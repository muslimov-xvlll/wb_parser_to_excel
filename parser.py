import time
import urllib.parse
import pandas as pd
from curl_cffi import requests
from typing import Dict, List, Optional, Tuple


def get_basket_number(article: int) -> str:
    """
    Рассчитывает номер корзины (CDN-сервера) Wildberries на основе артикула.
    Логика шардирования основана на реверс-инжиниринге.
    """
    # Шардирование по 'томам' (по 100 000 артикулов)
    vol = article // 100000

    # Жесткое сопоставление томов серверам
    if vol <= 143:
        return "01"
    elif vol <= 287:
        return "02"
    elif vol <= 431:
        return "03"
    elif vol <= 719:
        return "04"
    elif vol <= 1007:
        return "05"
    elif vol <= 1061:
        return "06"
    elif vol <= 1115:
        return "07"
    elif vol <= 1169:
        return "08"
    elif vol <= 1313:
        return "09"
    elif vol <= 1601:
        return "10"
    elif vol <= 1655:
        return "11"
    elif vol <= 1919:
        return "12"
    elif vol <= 2045:
        return "13"
    elif vol <= 2289:
        return "14"
    elif vol <= 2419:
        return "15"
    elif vol <= 2663:
        return "16"
    elif vol <= 2879:
        return "17"
    elif vol <= 3023:
        return "18"
    elif vol <= 3167:
        return "19"
    elif vol <= 3311:
        return "20"
    elif vol <= 3455:
        return "21"
    elif vol <= 3599:
        return "22"
    elif vol <= 3743:
        return "23"
    elif vol <= 3887:
        return "24"
    elif vol <= 4031:
        return "25"
    elif vol <= 4175:
        return "26"
    elif vol <= 4319:
        return "27"
    elif vol <= 4463:
        return "28"
    elif vol <= 4607:
        return "29"
    elif vol <= 4751:
        return "30"
    elif vol <= 4895:
        return "31"
    elif vol <= 5039:
        return "32"
    elif vol <= 5183:
        return "33"
    elif vol <= 5327:
        return "34"
    elif vol <= 5471:
        return "35"
    elif vol <= 5615:
        return "36"
    return "37"  # По умолчанию для самых новых артикулов


def get_item_details(article: int) -> Tuple[str, str, str, str]:
    """
    Запрашивает расширенную информацию о товаре с CDN-серверов WB:
    описание, характеристики, ссылки на фото и страну производства.
    """
    vol = article // 100000
    part = article // 1000
    basket = get_basket_number(article)

    url = f"https://basket-{basket}.wbcontent.net/vol{vol}/part{part}/{article}/info/ru/card.json"

    # Заголовки для имитации запроса с официального сайта
    headers = {
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.9",
        "Origin": "https://www.wildberries.ru",
        "Referer": "https://www.wildberries.ru/"
    }

    description, characteristics, country = "", "", ""
    photos = []

    try:
        # Используем чуть больший таймаут для стабильности.
        response = requests.get(url, headers=headers, timeout=10, impersonate="chrome120")

        if response.status_code == 200:
            data = response.json()
            description = data.get('description', '')

            # Парсинг характеристик из списка options
            options = data.get('options', [])
            char_list = []

            for opt in options:
                name = opt.get('name', '')
                value = opt.get('value', '')
                char_list.append(f"{name}: {value}")

                # Извлекаем страну для последующей фильтрации
                if name == "Страна производства":
                    country = value

            characteristics = " | ".join(char_list)

            # Формируем ссылки на изображения товара
            photo_count = data.get('media', {}).get('photo_count', 1)
            for i in range(1, photo_count + 1):
                photos.append(
                    f"https://basket-{basket}.wbcontent.net/vol{vol}/part{part}/{article}/images/big/{i}.webp")

    except Exception as e:
        # Логируем ошибку
        print(f"[!] Ошибка загрузки деталей для {article}: {e}")

    return description, characteristics, ",".join(photos), country


def get_wb_data(query: str) -> Optional[Dict]:
    """
    Выполняет поиск товаров на Wildberries по заданному запросу и возвращает JSON-ответ.
    """
    encoded_query = urllib.parse.quote(query)
    url = f"https://search.wb.ru/exactmatch/ru/common/v4/search?appType=1&curr=rub&dest=-1257786&query={encoded_query}&resultset=catalog"

    session = requests.Session(impersonate="chrome120")
    session.headers.update({
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://www.wildberries.ru",
        "Referer": "https://www.wildberries.ru/"
    })

    try:
        # Прогревочный запрос на главную для получения Cookies
        session.get("https://www.wildberries.ru/", timeout=10)
        time.sleep(1)

        response = session.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()

        print(f"Ошибка API. Статус: {response.status_code}")
        return None

    except Exception as e:
        print(f"Сетевая ошибка при поиске: {e}")
        return None


def parse_products(json_data: Dict) -> List[Dict]:
    """
    Парсит JSON-ответ от поискового API, собирает базовые и детальные данные
    для каждого товара в список словарей.
    """
    parsed_items = []

    products_list = json_data.get("products", [])

    print(f"Обработка {len(products_list)} товаров...")

    for idx, item in enumerate(products_list, 1):
        article = item.get('id')
        print(f"{idx}. Обработка артикула: {article}")

        name = item.get('name')
        brand = item.get('brand')
        # Учитываем, что рейтинг может быть в разных ключах.
        rating = item.get('reviewRating') or item.get('rating', 0)
        feedbacks = item.get('feedbacks', 0)

        # Вычисляем цену
        price = None
        sizes = item.get('sizes', [])
        if sizes:
            raw_price = sizes[0].get('price', {}).get('product')
            if raw_price:
                price = raw_price / 100

        # Список размеров в строку через запятую.
        sizes_str = ", ".join([size.get('origName') for size in sizes if size.get('origName')])

        supplier_id = item.get('supplierId')
        total_qty = item.get('totalQuantity', 0)

        product_link = f"https://www.wildberries.ru/catalog/{article}/detail.aspx"
        seller_link = f"https://www.wildberries.ru/seller/{supplier_id}" if supplier_id else ""

        # Добираем недостающие данные с CDN.
        description, characteristics, photos, country = get_item_details(article)

        parsed_items.append({
            'Ссылка на товар': product_link,
            'Артикул': article,
            'Название': name,
            'Цена': price,
            'Описание': description,
            'Ссылки на изображения через запятую': photos,
            'Все характеристики с сохранением их структуры': characteristics,
            'Название селлера': brand,
            'Ссылка на селлера': seller_link,
            'Размеры товара через запятую': sizes_str,
            'Остатки по товару (число)': total_qty,
            'Рейтинг': rating,
            'Количество отзывов': feedbacks,
            'Страна': country
        })

        # Пауза для снижения нагрузки на CDN-серверы и предотвращения блокировок.
        time.sleep(0.3)

    return parsed_items


def main():
    """
    Точка входа в скрипт. Координирует процесс поиска, парсинга и сохранения в Excel.
    """
    query = "Пальто из натуральной шерсти"
    print(f"Начинаем парсинг по запросу: {query}...")

    data = get_wb_data(query)

    if not data:
        print("Данные не получены. Завершение работы.")
        return

    all_products = parse_products(data)

    if all_products:
        # Преобразование данных в таблицу pandas DataFrame.
        df = pd.DataFrame(all_products)

        # Удаляем техническую колонку "Страна" перед сохранением полного каталога.
        df_full = df.drop(columns=['Страна'], errors='ignore')
        df_full.to_excel('wildberries_full_catalog.xlsx', index=False)
        print(f"Полный каталог сохранен в 'wildberries_full_catalog.xlsx' (строк: {len(df_full)})")

        condition = (
                (df['Рейтинг'] >= 4.5) &
                (df['Цена'] <= 10000) &
                (df['Страна'] == 'Россия')
        )
        filtered_df = df[condition]

        # Удаляем колонку "Страна" из финальной выборки.
        filtered_df = filtered_df.drop(columns=['Страна'], errors='ignore')

        filtered_df.to_excel('wildberries_filtered_catalog.xlsx', index=False)
        print(f"Выборка сохранена в 'wildberries_filtered_catalog.xlsx' (строк: {len(filtered_df)})")


if __name__ == "__main__":
    main()