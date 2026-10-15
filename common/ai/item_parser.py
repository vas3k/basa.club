from dataclasses import dataclass, field

from common.ai.core import OPENAI_MODEL_DUMB, ask_llm_structured, schema_from
from common.contacts import CONTACTS
from common.data.categories import CATEGORIES
from items.models import Item

category_parts = []
for node in CATEGORIES:
    children = ", ".join(f"{child.id} «{child.name}»" for child in node.children)
    category_parts.append(f"{node.id} «{node.name}»: {children}")
CATEGORY_CATALOG = "; ".join(category_parts)

PREFIX_CHOICES = ", ".join(f"{value} ({label})" for value, label in Item.PREFIXES)
CONTACT_TYPE_CHOICES = ", ".join(f"{row['type']} ({row['label']})" for row in CONTACTS)
TITLE_MAX = Item._meta.get_field("title").max_length
LOCATION_MAX = Item._meta.get_field("location").max_length
PROMO_CODE_MAX = Item._meta.get_field("promo_code").max_length


@dataclass
class ParsedContact:
    type: str = field(metadata={
        "description": f"Одно из: {CONTACT_TYPE_CHOICES}",
        "enum": [row["type"] for row in CONTACTS],
    })
    text: str = field(metadata="Номер, ник или ссылка")
    comment: str = field(metadata="Короткое пояснение. Имя можно. Пустая строка, если пояснения нет")


@dataclass
class ParsedItem:
    error: str = field(metadata=(
        "Пустая строка, если сообщение — объявление, рекомендация или реклама и карточка заполнена. "
        "Иначе короткое объяснение по-русски, почему это не объявление или каких данных не хватает. "
        "Не выдумывай карточку: остальные поля оставь пустыми."
    ))
    prefix: str = field(metadata={
        "description": f"Одно из: {PREFIX_CHOICES}. Пустая строка, если автор не ищет",
        "enum": ["", *[value for value, label in Item.PREFIXES]],
    })
    title: str = field(metadata=(
        f"Короткий точный заголовок, до {TITLE_MAX} символов. "
        "Имя человека/компании можно, район города или другой ориентир можно. Телефоны, ссылки и промокоды и любые приватные данные никогда не добавляй сюда."
    ))
    description: str = field(metadata=(
        "Комментарий, опыт, отзыв или пояснение лично автора. "
        "Пустая строка, если их нет. Не копируй сюда никакие контакты или приватные данные."
    ))
    location: str = field(metadata=f"Точный адрес или ссылка на карту, до {LOCATION_MAX} символов. Пустая строка, если адреса нет")
    contacts: list = field(metadata={
        "description": "Найденные контакты. Пустой список, если их нет",
        "items": ParsedContact,
    })
    promo_code: str = field(metadata=f"Промокод как в тексте, до {PROMO_CODE_MAX} символов. Пустая строка, если его нет")
    category: str = field(metadata=f"id корневой категории. {CATEGORY_CATALOG}")
    subcategory: str = field(metadata=(
        "id подкатегории выбранной категории. "
        "Если тема узнаваема, выбери ближайшую, а не пустую строку"
    ))
    country: str = field(metadata="Страна. Пустая строка, если страну нельзя понять")
    city: str = field(metadata="Город. Пустая строка, если города нет")


ITEM_SCHEMA = schema_from(ParsedItem)
ITEM_FIELDS = "\n".join(
    f"{name} — {prop['description']}" for name, prop in ITEM_SCHEMA["properties"].items()
)
CONTACT_FIELDS = "\n".join(
    f"{name} — {prop['description']}"
    for name, prop in ITEM_SCHEMA["properties"]["contacts"]["items"]["properties"].items()
)

ITEM_PARSER_PROMPT = f"""Разбери сообщение из чата и заполни карточку объявления.

Пиши текстовые поля по-русски. Не выдумывай ничего от себя. Телефоны, ники, ссылки, промокоды и написание улиц оставляй как в сообщении. Название чата можно использовать как подсказку о городе. Если это не объявление, рекомендация или реклама, или данных не хватает, напиши причину в error и не заполняй карточку.

Поля карточки:
{ITEM_FIELDS}

Поля контакта в contacts:
{CONTACT_FIELDS}
"""


def parse_item(text, model=OPENAI_MODEL_DUMB):
    message = (text or "").strip()
    if not message:
        raise ValueError("Empty item text")

    data = ask_llm_structured(ITEM_PARSER_PROMPT, message, ITEM_SCHEMA, model=model)
    data["contacts"] = [ParsedContact(**row) for row in data["contacts"]]
    return ParsedItem(**data)
