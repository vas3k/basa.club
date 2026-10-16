from dataclasses import dataclass, field


@dataclass
class Category:
    id: str
    name: str
    icon: str = ""
    children: list = field(default_factory=list)
    description: str = ""
    metadata: dict = field(default_factory=dict)


CATEGORIES = [
    Category(
        "services",
        "Услуги",
        "❤️",
        [
            Category("auto", "Автосервисы", '<i class="fas fa-car"></i>'),
            Category("doctors", "Врачи и терапевты", '<i class="fas fa-user-md"></i>'),
            Category("lawyers", "Юристы и адвокаты", '<i class="fas fa-balance-scale"></i>'),
            Category("babies", "Дети", '<i class="fas fa-baby"></i>'),
            Category("cleaning", "Клининг", '<i class="fas fa-broom"></i>'),
            Category("home", "Работы по дому", '<i class="fas fa-home"></i>'),
            Category("movers", "Грузчики", '<i class="fas fa-dolly"></i>'),
            Category("repair", "Ремонт техники", '<i class="fas fa-tools"></i>'),
            Category("pets", "Питомцы", '<i class="fas fa-paw"></i>'),
            Category("rental", "Аренда", '<i class="fas fa-toolbox"></i>'),
            Category("tutors", "Репетиторы", '<i class="fas fa-book"></i>'),
            Category("photo", "Фото и видео", '<i class="fas fa-camera"></i>'),
            Category("accountants", "Налоги и бухгалтеры", '<i class="fas fa-file-invoice"></i>'),
            Category("beauty", "Красота", '<i class="fas fa-cut"></i>'),
            Category("translation", "Переводчики", '<i class="fas fa-language"></i>'),
            Category("other", "Другое", '<i class="fas fa-ellipsis-h"></i>'),
        ],
    ),
    Category(
        "coupons",
        "Купоны и скидки",
        "🎟️",
        [
            Category("software", "Софт и подписки", '<i class="fas fa-desktop"></i>'),
            Category("stores", "Магазины", '<i class="fas fa-store"></i>'),
            Category("travel", "Путешествия", '<i class="fas fa-plane"></i>'),
            Category("lifestyle", "Спорт и красота", '<i class="fas fa-spa"></i>'),
            Category("education", "Образование", '<i class="fas fa-graduation-cap"></i>'),
            Category("fun", "Развлечения", '<i class="fas fa-ticket-alt"></i>'),
            Category("other", "Другое", '<i class="fas fa-ellipsis-h"></i>'),
        ],
        metadata={"include_online": True},
    ),
]
